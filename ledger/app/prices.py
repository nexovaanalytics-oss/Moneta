# SPDX-License-Identifier: EUPL-1.2
"""XMR/EUR-Kurse zum Zuflusszeitpunkt ermitteln (CoinGecko) und festschreiben.

Ablauf:
- Alle 30 Minuten werden die 5-Minuten-Kurse der letzten 24 Stunden geladen und lokal
  gespeichert (Tabelle price_points). Die Abfrage ist unabhängig von Auszahlungen –
  CoinGecko erfährt also nicht, wann deine Mining-Adresse etwas erhalten hat.
- Für jeden Zufluss ohne Kurs wird der nächstgelegene lokale Kurspunkt (max. 15 Min.
  Abstand) verwendet.
- Fehlt ein lokaler Punkt (z. B. weil der Ledger länger aus war), wird der Tageskurs
  (00:00 UTC) des Zuflusstags abgefragt; dabei wird nur das Datum übermittelt.
- Vorrang haben manuelle Kurse aus <data>/kurse_manuell.csv (TXID oder Datum ; EUR-Kurs).

Ein einmal gespeicherter Kurs wird nicht mehr verändert (nachvollziehbare Dokumentation).
Hinweis: Die kostenlose CoinGecko-API liefert historische Daten nur für etwa ein Jahr zurück.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal

import db
from config import Config

log = logging.getLogger("prices")
API = "https://api.coingecko.com/api/v3"
SOURCE_5MIN = "CoinGecko 5-Min-Kurs"
MAX_DISTANCE_S = 15 * 60
HISTORY_INTERVAL_S = 10 * 60  # festes Raster, unabhängig von Auszahlungen (D-05)


def _now() -> float:  # in Tests ersetzbar
    return time.time()


def _get(cfg: Config, path: str, params: dict) -> dict:
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    headers = {"Accept": "application/json", "User-Agent": "xmr-ledger"}
    if cfg.coingecko_api_key:
        headers["x-cg-demo-api-key"] = cfg.coingecko_api_key
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _q(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.0001"))


def update_history(cfg: Config) -> int:
    """5-Minuten-Kurse der letzten 24 h lokal speichern."""
    data = _get(cfg, "/coins/monero/market_chart", {"vs_currency": "eur", "days": "1"})
    pts = data.get("prices") or []
    with db.write_lock:
        c = db.get()
        before = c.total_changes
        c.executemany("INSERT OR IGNORE INTO price_points(ts, eur, source) VALUES(?,?,?)",
                      [(int(p[0] / 1000), str(_q(p[1])), SOURCE_5MIN) for p in pts if p and p[1] is not None])
        c.commit()
        added = c.total_changes - before
    db.set_meta("price_history_last", str(db.now()))
    return added


def current_price_point(cfg: Config) -> tuple[Decimal, int] | None:
    """Jüngster lokal gespeicherter Kurs mit Zeitpunkt (höchstens 2 Stunden alt)."""
    now = _now()
    row = db.get().execute("SELECT ts, eur FROM price_points WHERE ts <= ? ORDER BY ts DESC LIMIT 1",
                           (int(now) + 300,)).fetchone()
    if row and now - row["ts"] < 2 * 3600:
        return Decimal(row["eur"]), int(row["ts"])
    return None


def current_price(cfg: Config) -> Decimal | None:
    """Jüngster lokal gespeicherter Kurs (höchstens 2 Stunden alt)."""
    pt = current_price_point(cfg)
    return None if pt is None else pt[0]


def _manual_overrides(cfg: Config) -> dict[str, Decimal]:
    path = os.path.join(cfg.data_dir, "kurse_manuell.csv")
    out: dict[str, Decimal] = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(";")]
            if len(parts) < 2:
                continue
            raw = parts[1].replace(" ", "")
            if "," in raw:
                raw = raw.replace(".", "").replace(",", ".")
            try:
                out[parts[0]] = Decimal(raw)
            except Exception:  # noqa: BLE001
                log.warning("kurse_manuell.csv: Zeile ignoriert: %s", line)
    return out


def _local_point(ts: int) -> tuple[Decimal, int] | None:
    c = db.get()
    before = c.execute("SELECT ts, eur FROM price_points WHERE ts <= ? ORDER BY ts DESC LIMIT 1", (ts,)).fetchone()
    after = c.execute("SELECT ts, eur FROM price_points WHERE ts > ? ORDER BY ts ASC LIMIT 1", (ts,)).fetchone()
    cands = [r for r in (before, after) if r is not None and abs(r["ts"] - ts) <= MAX_DISTANCE_S]
    if not cands:
        return None
    best = min(cands, key=lambda r: abs(r["ts"] - ts))
    return Decimal(best["eur"]), best["ts"]


def price_for(cfg: Config, txid: str, ts: int, manual: dict[str, Decimal] | None = None,
              allow_daily: bool = True) -> tuple[Decimal, int, str] | None:
    manual = _manual_overrides(cfg) if manual is None else manual
    local_day = datetime.fromtimestamp(ts, cfg.tz).date().isoformat()
    if txid in manual:
        return manual[txid], ts, "manuell (TXID)"
    if local_day in manual:
        return manual[local_day], ts, f"manuell (Tageskurs {local_day})"

    pt = _local_point(ts)
    if pt:
        eur, pts = pt
        return eur, pts, f"{SOURCE_5MIN} (Abstand {abs(pts - ts) / 60:.0f} Min.)"

    if not allow_daily:
        return None
    utc_day = datetime.fromtimestamp(ts, timezone.utc)
    data = _get(cfg, "/coins/monero/history", {"date": utc_day.strftime("%d-%m-%Y"), "localization": "false"})
    eur = data.get("market_data", {}).get("current_price", {}).get("eur")
    if eur is None:
        return None
    day_ts = int(datetime(utc_day.year, utc_day.month, utc_day.day, tzinfo=timezone.utc).timestamp())
    return _q(eur), day_ts, f"CoinGecko Tageskurs {utc_day.date().isoformat()} 00:00 UTC"


def fill_missing(cfg: Config) -> int:
    # Nur Mining-Zuflüsse brauchen einen Kurs (sonstige Zugänge sind keine Einnahmen)
    rows = db.get().execute("SELECT txid, ts FROM inflows WHERE kind='block' AND price_eur IS NULL "
                            "ORDER BY ts").fetchall()
    if not rows:
        return 0
    manual = _manual_overrides(cfg)
    done = 0
    for r in rows:
        # Solange der Zufluss noch im 24-h-Fenster der 5-Minuten-Kurse liegt, auf den nächsten
        # Abruf warten statt auf den ungenaueren Tageskurs auszuweichen.
        recent = _now() - r["ts"] < 20 * 3600
        try:
            res = price_for(cfg, r["txid"], r["ts"], manual=manual, allow_daily=not recent)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                log.info("CoinGecko-Ratenlimit erreicht – später weiter")
                break
            log.warning("Kurs für %s nicht abrufbar: %s", r["txid"][:12], e)
            continue
        except Exception as e:  # noqa: BLE001
            log.warning("Kurs für %s nicht abrufbar: %s", r["txid"][:12], e)
            continue
        if res is None:
            continue
        eur, pts, src = res
        with db.write_lock:
            c = db.get()
            c.execute("UPDATE inflows SET price_eur=?, price_ts=?, price_source=? WHERE txid=? AND price_eur IS NULL",
                      (str(eur), pts, src, r["txid"]))
            c.commit()
        done += 1
        if "Tageskurs" in src and not src.startswith("manuell"):
            time.sleep(4)  # freundlich zur kostenlosen API
    return done


def loop(cfg: Config, stop) -> None:
    last = 0.0
    while not stop.is_set():
        if time.time() - last >= HISTORY_INTERVAL_S:
            try:
                n = update_history(cfg)
                last = time.time()
                log.debug("%d neue Kurspunkte", n)
            except Exception as e:  # noqa: BLE001
                log.warning("Kurshistorie nicht abrufbar: %s", e)
        try:
            fill_missing(cfg)
        except Exception:  # noqa: BLE001
            log.exception("Kurszuordnung: unerwarteter Fehler")
        stop.wait(300)
