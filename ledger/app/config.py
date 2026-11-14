# SPDX-License-Identifier: EUPL-1.2
"""Konfiguration aus config.toml laden."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo


@dataclass
class Miner:
    name: str
    url: str
    token: str = ""
    watts: float = 0.0
    note: str = ""


@dataclass
class Tariff:
    valid_from: date
    ct_per_kwh: float


@dataclass
class Config:
    # Wallet
    address: str
    view_key: str
    restore_height: int
    wallet_password: str
    wallet_file: str = "mining-viewonly"
    wallet_rpc_url: str = "http://wallet-rpc:18082/json_rpc"
    # Allgemein
    timezone: str = "Europe/Berlin"
    data_dir: str = "/data"
    # Web
    web_port: int = 8090
    web_user: str = "admin"
    web_password: str = ""
    # Kurse
    coingecko_api_key: str = ""
    # Eigener Node (eingeschränkter RPC) für Difficulty/Blockbelohnung; leer = aus
    node_rpc_url: str = "http://monerod:18089/json_rpc"
    # Strom
    poll_seconds: int = 60
    nas_extra_watts: float = 0.0
    nas_note: str = ""
    tariffs: list[Tariff] = field(default_factory=list)
    miners: list[Miner] = field(default_factory=list)

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def tariff_at(self, ts: float) -> float:
        """Strompreis in ct/kWh, der zum Zeitpunkt ts gilt."""
        d = datetime.fromtimestamp(ts, self.tz).date()
        valid = [t for t in self.tariffs if t.valid_from <= d]
        if not valid:
            return self.tariffs[0].ct_per_kwh if self.tariffs else 0.0
        return max(valid, key=lambda t: t.valid_from).ct_per_kwh


def _as_date(v) -> date:
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v))


def load(path: str) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    w = raw.get("wallet", {})
    web = raw.get("web", {})
    pr = raw.get("prices", {})
    pw = raw.get("power", {})
    gen = raw.get("general", {})
    node = raw.get("node", {})

    for key in ("address", "view_key", "restore_height", "wallet_password"):
        if key not in w or w[key] in ("", None):
            raise SystemExit(f"config.toml: [wallet] {key} fehlt")
    if not str(w["address"]).startswith("4") or len(str(w["address"])) != 95:
        raise SystemExit("config.toml: [wallet] address muss die Hauptadresse (95 Zeichen, beginnt mit 4) sein")
    if not web.get("password"):
        raise SystemExit("config.toml: [web] password fehlt – das Dashboard zeigt Finanzdaten")

    tariffs = [Tariff(_as_date(t["valid_from"]), float(t["ct_per_kwh"])) for t in pw.get("tariff", [])]
    tariffs.sort(key=lambda t: t.valid_from)
    if not tariffs:
        raise SystemExit("config.toml: mindestens ein [[power.tariff]] mit valid_from und ct_per_kwh angeben")

    miners = [
        Miner(
            name=str(m["name"]),
            url=str(m["url"]).rstrip("/"),
            token=str(m.get("token", "")),
            watts=float(m.get("watts", 0.0)),
            note=str(m.get("note", "")),
        )
        for m in raw.get("miner", [])
    ]

    return Config(
        address=str(w["address"]),
        view_key=str(w["view_key"]),
        restore_height=int(w["restore_height"]),
        wallet_password=str(w["wallet_password"]),
        wallet_file=str(w.get("wallet_file", "mining-viewonly")),
        wallet_rpc_url=str(w.get("rpc_url", "http://wallet-rpc:18082/json_rpc")),
        timezone=str(gen.get("timezone", "Europe/Berlin")),
        data_dir=str(gen.get("data_dir", "/data")),
        web_port=int(web.get("port", 8090)),
        web_user=str(web.get("user", "admin")),
        web_password=str(web["password"]),
        coingecko_api_key=str(pr.get("coingecko_api_key", "")),
        node_rpc_url=str(node.get("rpc_url", "http://monerod:18089/json_rpc")),
        poll_seconds=int(pw.get("poll_seconds", 60)),
        nas_extra_watts=float(pw.get("nas_extra_watts", 0.0)),
        nas_note=str(pw.get("nas_note", "")),
        tariffs=tariffs,
        miners=miners,
    )
