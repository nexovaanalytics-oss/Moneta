# SPDX-License-Identifier: EUPL-1.2
"""Difficulty und Blockbelohnung vom eigenen Monero-Node (eingeschränkter RPC).

Grundlage für den rechnerischen Gegenwert auf der Seite „Auswertung“:
erwartete XMR = Hashes / Difficulty x Blockbelohnung. Abgefragt wird nur der eigene Node,
es geht nichts ins Internet. Gespeichert wird höchstens ein Block je Stunde.
"""
from __future__ import annotations

import bisect
import json
import logging
import time
import urllib.request
from decimal import Decimal

import db
import prices
from config import Config

log = logging.getLogger("network")
SAMPLE_INTERVAL_S = 3600
RANGE_MAX = 1000          # Obergrenze des eingeschränkten RPC für get_block_headers_range
BACKFILL_MAX_DAYS = 40    # Minutenwerte reichen 30 Tage zurück
BLOCK_TIME_S = 120


class NodeError(Exception):
    pass


def rpc(cfg: Config, method: str, params: dict | None = None, timeout: int = 30) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": "0", "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(cfg.node_rpc_url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    if "error" in data:
        raise NodeError(data["error"].get("message", str(data["error"])))
    return data["result"]


def _store(headers: list[dict]) -> int:
    """Je Stunde (nach Blockzeit) höchstens einen Block speichern."""
    added = 0
    with db.write_lock:
        c = db.get()
        hours = {r[0] for r in c.execute("SELECT ts - ts % 3600 FROM network_samples")}
        for h in sorted(headers, key=lambda x: x["height"]):
            hour = int(h["timestamp"]) - int(h["timestamp"]) % 3600
            if hour in hours:
                continue
            c.execute("INSERT OR IGNORE INTO network_samples(height, ts, difficulty, reward) VALUES(?,?,?,?)",
                      (int(h["height"]), int(h["timestamp"]), int(h["difficulty"]), int(h["reward"])))
            hours.add(hour)
            added += 1
        c.commit()
    return added


def sample_once(cfg: Config) -> int:
    hdr = rpc(cfg, "get_last_block_header")["block_header"]
    return _store([hdr])


def backfill(cfg: Config, since_ts: int) -> int:
    """Stündliche Werte ab since_ts nachholen (einmalig, z. B. für Minutenwerte vor dem Update)."""
    since_ts = max(int(since_ts), int(time.time()) - BACKFILL_MAX_DAYS * 86400)
    first = db.get().execute("SELECT MIN(ts) FROM network_samples").fetchone()[0]
    if first is not None and first <= since_ts + 3600:
        return 0
    top = int(rpc(cfg, "get_info")["height"]) - 1
    end = top if first is None else int(db.get().execute("SELECT MIN(height) FROM network_samples").fetchone()[0]) - 1
    start = max(0, top - (int(time.time()) - since_ts) // BLOCK_TIME_S - 60)
    added = 0
    h = start
    while h <= end:
        hi = min(h + RANGE_MAX - 1, end)
        res = rpc(cfg, "get_block_headers_range", {"start_height": h, "end_height": hi}, timeout=120)
        added += _store(res.get("headers") or [])
        h = hi + 1
    return added


def samples_between(start: int, end: int) -> list[tuple[int, int, int]]:
    """(ts, difficulty, reward) im Zeitraum, mit je einem Wert davor und danach."""
    c = db.get()
    rows = [tuple(r) for r in c.execute(
        "SELECT ts, difficulty, reward FROM network_samples WHERE ts BETWEEN ? AND ? ORDER BY ts", (start, end))]
    before = c.execute("SELECT ts, difficulty, reward FROM network_samples WHERE ts < ? ORDER BY ts DESC LIMIT 1",
                       (start,)).fetchone()
    after = c.execute("SELECT ts, difficulty, reward FROM network_samples WHERE ts > ? ORDER BY ts LIMIT 1",
                      (end,)).fetchone()
    return ([tuple(before)] if before else []) + rows + ([tuple(after)] if after else [])


def nearest(samples: list[tuple[int, int, int]], ts: int, max_gap: int = 6 * 3600):
    """Nächstgelegener Wert (höchstens max_gap entfernt) oder None."""
    if not samples:
        return None
    keys = [s[0] for s in samples]
    i = bisect.bisect_left(keys, ts)
    cand = [samples[j] for j in (i - 1, i) if 0 <= j < len(samples)]
    best = min(cand, key=lambda s: abs(s[0] - ts))
    return best if abs(best[0] - ts) <= max_gap else None


def loop(cfg: Config, stop) -> None:
    if not cfg.node_rpc_url:
        log.info("Kein [node] rpc_url – Difficulty wird nicht erfasst")
        return
    backfilled = False
    while not stop.is_set():
        try:
            if not backfilled:
                oldest = db.get().execute("SELECT MIN(ts) FROM power_samples").fetchone()[0]
                n = backfill(cfg, oldest if oldest is not None else int(time.time()) - 86400)
                if n:
                    log.info("%d Netzwerkwerte nachgeholt", n)
                backfilled = True
            sample_once(cfg)
            db.set_meta("network_error", "")
        except Exception as e:  # noqa: BLE001  – Node startet, synchronisiert oder ist nicht erreichbar
            db.set_meta("network_error", str(e))
            log.warning("Node-Abfrage fehlgeschlagen: %s", e)
        stop.wait(SAMPLE_INTERVAL_S)


def economics(cfg: Config, now: float | None = None) -> dict | None:
    """Kennzahlen für die Thread-Wahl beim Einmessen (GET /api/moneta, nur Anzeige, nichts Steuerrelevantes).

    Rechnerischer Ertrag je H/s und Tag = 86.400 / Difficulty x Blockbelohnung x Kurs, Stromkosten je Watt und
    Tag = 0,024 kWh x Tarif. Grundlage: jüngster Wert vom eigenen Node, jüngster lokaler Kurs (höchstens
    2 Stunden alt), aktueller Tarif aus der config.toml. Fehlt Node- oder Kurswert: None.
    """
    now = time.time() if now is None else now
    row = db.get().execute("SELECT ts, difficulty, reward FROM network_samples ORDER BY ts DESC LIMIT 1").fetchone()
    pt = prices.current_price_point(cfg)
    if row is None or pt is None or not row["difficulty"]:
        return None
    price, price_ts = pt
    reward_xmr = Decimal(int(row["reward"])) / Decimal(10 ** 12)
    eur_per_hs_day = Decimal(86400) / Decimal(int(row["difficulty"])) * reward_xmr * price
    ct = Decimal(str(cfg.tariff_at(now)))
    eur_per_w_day = Decimal("0.024") * ct / Decimal(100)
    return {"difficulty": int(row["difficulty"]), "reward_xmr": float(reward_xmr), "network_ts": int(row["ts"]),
            "price_eur": float(price), "price_ts": int(price_ts), "ct_per_kwh": float(ct),
            "eur_per_hs_day": float(eur_per_hs_day), "eur_per_w_day": float(eur_per_w_day)}
