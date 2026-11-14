# SPDX-License-Identifier: EUPL-1.2
"""Mining-Laufzeit der Rechner über die XMRig-HTTP-API erfassen und Stromkosten berechnen.

Methode: Je Abfrage wird geprüft, ob XMRig erreichbar ist, nicht pausiert und
Hashrate liefert. Nur dann wird das Abfrageintervall als Mining-Zeit gezählt.
Kosten = gemessener Mehrverbrauch (Watt) x Mining-Zeit x Strompreis.
Watt und Strompreis werden zum Zeitpunkt der Erfassung festgeschrieben;
spätere Änderungen in config.toml wirken nur für die Zukunft.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime

import activity
import db
import devices
from config import Config, Miner

log = logging.getLogger("miners")
NAS_DEVICE = activity.NAS_DEVICE

_live: dict[str, dict] = {}  # letzter Status je Gerät fürs Dashboard


def live_status() -> dict[str, dict]:
    return dict(_live)


def current(cfg: Config, now: float | None = None) -> list[Miner]:
    """Alle abzufragenden Rechner: [[miner]] aus config.toml plus im Dashboard gekoppelte und freigegebene.
    Watt der gekoppelten Rechner = Wert, der zum Zeitpunkt now gilt."""
    return list(cfg.miners) + devices.active_miners(now)


def fetch_summary(m: Miner, timeout: int = 5) -> dict | None:
    headers = {"Accept": "application/json"}
    if m.token:
        headers["Authorization"] = f"Bearer {m.token}"
    for path in ("/2/summary", "/1/summary"):  # /1 als Rückfall für ältere XMRig-Versionen
        req = urllib.request.Request(f"{m.url}{path}", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            if e.code in (401, 403):
                _auth_warn(m)
            return None
        except Exception:  # noqa: BLE001  – Rechner aus, schläft oder XMRig läuft nicht
            return None
    return None


_warned: set[str] = set()


def _auth_warn(m: Miner) -> None:
    if m.name not in _warned:
        where = "token in config.toml" if m.source == "config" else "Kopplung im Dashboard (Geräte)"
        log.warning("%s: XMRig-API lehnt das Token ab – %s prüfen", m.name, where)
        _warned.add(m.name)


def _hashrate(summary: dict) -> float:
    total = (summary.get("hashrate") or {}).get("total") or []
    for v in total[:2]:  # 10s, dann 60s
        if v:
            return float(v)
    return 0.0


def record(cfg: Config, device: str, ts: float, reachable: bool, mining: bool,
           hashrate: float, seconds: int, watts: float) -> None:
    tariff = cfg.tariff_at(ts)
    kwh = watts * seconds / 3_600_000 if mining else 0.0
    cost = kwh * tariff / 100
    day = datetime.fromtimestamp(ts, cfg.tz).date().isoformat()
    with db.write_lock:
        c = db.get()
        c.execute("INSERT INTO power_samples(ts, device, reachable, mining, hashrate, seconds, watts, tariff_ct) "
                  "VALUES(?,?,?,?,?,?,?,?)",
                  (int(ts), device, int(reachable), int(mining), hashrate, seconds if mining else 0, watts, tariff))
        c.execute(
            """INSERT INTO power_daily(day, device, mining_seconds, kwh, cost_eur, hr_sum, hr_n, watts_last, tariff_last)
               VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(day, device) DO UPDATE SET
                 mining_seconds = mining_seconds + excluded.mining_seconds,
                 kwh = kwh + excluded.kwh,
                 cost_eur = cost_eur + excluded.cost_eur,
                 hr_sum = hr_sum + excluded.hr_sum,
                 hr_n = hr_n + excluded.hr_n,
                 watts_last = excluded.watts_last,
                 tariff_last = excluded.tariff_last""",
            (day, device, seconds if mining else 0, kwh, cost,
             hashrate if mining else 0.0, 1 if mining and hashrate > 0 else 0, watts, tariff))
        activity.add_hourly(c, device, ts, reachable, mining, hashrate, seconds, watts, tariff)
        c.commit()


def poll_once(cfg: Config, last: dict[str, float]) -> None:
    now = time.time()
    cap = 2 * cfg.poll_seconds

    for m in current(cfg, now):
        s = fetch_summary(m)
        reachable = s is not None
        paused = bool(s.get("paused")) if s else True
        hr = _hashrate(s) if s else 0.0
        mining = reachable and not paused and hr > 0
        prev = last.get(m.name)
        interval = int(min(max(now - prev, 0), cap)) if prev else cfg.poll_seconds
        last[m.name] = now
        record(cfg, m.name, now, reachable, mining, hr, interval, m.watts)
        _live[m.name] = {"reachable": reachable, "mining": mining, "paused": paused, "hashrate": hr,
                         "ts": now, "watts": m.watts,
                         "uptime": (s or {}).get("uptime"),
                         "shares_good": ((s or {}).get("results") or {}).get("shares_good")}

    if cfg.nas_extra_watts > 0:
        prev = last.get(NAS_DEVICE)
        interval = int(min(max(now - prev, 0), cap)) if prev else cfg.poll_seconds
        last[NAS_DEVICE] = now
        record(cfg, NAS_DEVICE, now, True, True, 0.0, interval, cfg.nas_extra_watts)


def cleanup(retention_days: int = 30) -> None:
    with db.write_lock:
        c = db.get()
        c.execute("DELETE FROM power_samples WHERE ts < ?", (int(time.time()) - retention_days * 86400,))
        c.commit()


def loop(cfg: Config, stop) -> None:
    last: dict[str, float] = {}
    n = 0
    while not stop.is_set():
        try:
            poll_once(cfg, last)
            n += 1
            if n % 1440 == 0:
                cleanup()
        except Exception:  # noqa: BLE001
            log.exception("Miner-Abfrage: unerwarteter Fehler")
        stop.wait(cfg.poll_seconds)
