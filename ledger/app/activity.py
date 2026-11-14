# SPDX-License-Identifier: EUPL-1.2
"""Auswertung des Mining-Betriebs über frei wählbare Zeiträume (Seite „Auswertung“).

Quellen: Minutenwerte (power_samples, 30 Tage), Stundenwerte (activity_hourly, unbegrenzt),
Difficulty/Blockbelohnung vom eigenen Node (network_samples), Kurse (price_points) und
Auszahlungen (inflows). Reine Anzeige – Steuergrundlage bleiben power_daily und inflows.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal

import db
import network
from config import Config

log = logging.getLogger("activity")
HOUR = 3600
PICO = 10 ** 12
NAS_DEVICE = "NAS (Node + Pool)"   # Pauschale für Node + Pool: zählt nur bei kWh und Kosten


def hour_of(ts: float) -> int:
    t = int(ts)
    return t - t % HOUR


def bucket_of(ts: float, seconds: int) -> int:
    """Stunde, in die eine Abfrage gebucht wird: Mitte des Intervalls, das sie abdeckt."""
    return hour_of(int(ts) - int(seconds) // 2)


def add_hourly(c, device: str, ts: float, reachable: bool, mining: bool, hashrate: float,
               seconds: int, watts: float, tariff_ct: float) -> None:
    """Eine Abfrage in die Stundenwerte buchen (innerhalb der Transaktion des Aufrufers)."""
    kwh = watts * seconds / 3_600_000 if mining else 0.0
    c.execute(
        """INSERT INTO activity_hourly(hour, device, polls, mining_s, paused_s, offline_s, hashes, hr_max, kwh, cost_eur)
           VALUES(?,?,1,?,?,?,?,?,?,?)
           ON CONFLICT(hour, device) DO UPDATE SET
             polls = polls + 1,
             mining_s = mining_s + excluded.mining_s,
             paused_s = paused_s + excluded.paused_s,
             offline_s = offline_s + excluded.offline_s,
             hashes = hashes + excluded.hashes,
             hr_max = MAX(hr_max, excluded.hr_max),
             kwh = kwh + excluded.kwh,
             cost_eur = cost_eur + excluded.cost_eur""",
        (bucket_of(ts, seconds), device,
         seconds if mining else 0,
         seconds if reachable and not mining else 0,
         seconds if not reachable else 0,
         (hashrate or 0.0) * seconds if mining else 0.0,
         (hashrate or 0.0) if mining else 0.0,
         kwh, kwh * tariff_ct / 100))


def _sample_rows(cfg: Config, start: int, end: int, device: str | None = None) -> list[dict]:
    """Minutenwerte mit Intervall je Abfrage. Bei Mining steht es in der Tabelle, sonst ergibt es sich
    aus dem Abstand zur vorigen Abfrage desselben Geräts (höchstens 2 x poll_seconds), wie bei der Erfassung."""
    cap = 2 * cfg.poll_seconds
    q = ("SELECT ts, device, reachable, mining, hashrate, seconds, watts, tariff_ct FROM power_samples "
         "WHERE ts >= ? AND ts < ?" + (" AND device = ?" if device else "") + " ORDER BY device, ts")
    args = (start - cap, end + cap) + ((device,) if device else ())
    out, prev = [], {}
    for r in db.get().execute(q, args):
        d = dict(r)
        p = prev.get(d["device"])
        prev[d["device"]] = d["ts"]
        if d["mining"]:
            iv = d["seconds"]
        else:
            iv = int(min(max(d["ts"] - p, 0), cap)) if p is not None else cfg.poll_seconds
        d["interval"] = iv
        if start <= d["ts"] - iv // 2 < end:   # Intervallmitte im Zeitraum
            out.append(d)
    return out


def backfill_hourly(cfg: Config) -> int:
    """Einmalig nach Migration 3: vorhandene Minutenwerte in Stundenwerte übernehmen."""
    if db.get_meta("activity_backfill_done"):
        return 0
    rows = _sample_rows(cfg, 0, 2 ** 62)
    with db.write_lock:
        c = db.get()
        if c.execute("SELECT COUNT(*) FROM activity_hourly").fetchone()[0] == 0:
            for d in rows:
                add_hourly(c, d["device"], d["ts"], bool(d["reachable"]), bool(d["mining"]), d["hashrate"] or 0.0,
                           d["interval"], d["watts"], d["tariff_ct"])
        c.execute("INSERT INTO meta(key, value) VALUES('activity_backfill_done', ?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(db.now()),))
        c.commit()
    if rows:
        log.info("%d Minutenwerte in Stundenwerte übernommen", len(rows))
    return len(rows)


# ---------- Zeiträume ----------
PRESETS = [("nacht", "Letzte Nacht"), ("24h", "24 Stunden"), ("7d", "7 Tage"), ("30d", "30 Tage"),
           ("monat", "Dieser Monat"), ("jahr", "Dieses Jahr")]


def preset_range(cfg: Config, key: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(cfg.tz)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if key == "nacht":
        # 18:00 bis 08:00 der letzten Nacht (vor 08:00 die laufende Nacht bis jetzt)
        end = today.replace(hour=8)
        if now < end:
            end = now
        return (today - timedelta(days=1)).replace(hour=18), end
    if key == "7d":
        return now - timedelta(days=7), now
    if key == "30d":
        return now - timedelta(days=30), now
    if key == "monat":
        return today.replace(day=1), now
    if key == "jahr":
        return today.replace(month=1, day=1), now
    return now - timedelta(hours=24), now


# ---------- Auswertung ----------
def _empty() -> dict:
    return {"polls": 0, "mining_s": 0, "paused_s": 0, "offline_s": 0, "hashes": 0.0, "hr_max": 0.0,
            "kwh": 0.0, "cost": 0.0, "exp_xmr": Decimal(0), "exp_missing_s": 0}


def analyse(cfg: Config, start: datetime, end: datetime) -> dict:
    s, e = int(start.timestamp()), int(end.timestamp())
    if e <= s:
        raise ValueError("Ende muss nach dem Beginn liegen")
    oldest = db.get().execute("SELECT MIN(ts) FROM power_samples").fetchone()[0]
    minute = oldest is not None and s >= oldest - 2 * cfg.poll_seconds

    # Buckets je (Stunde, Gerät) aus Minuten- oder Stundenwerten
    buckets: dict[tuple[int, str], dict] = {}
    segments: dict[str, list[list]] = {}
    if minute:
        for d in _sample_rows(cfg, s, e):
            b = buckets.setdefault((bucket_of(d["ts"], d["interval"]), d["device"]), _empty())
            iv, mining, reach = d["interval"], bool(d["mining"]), bool(d["reachable"])
            b["polls"] += 1
            if mining:
                b["mining_s"] += iv
                b["hashes"] += (d["hashrate"] or 0.0) * iv
                b["hr_max"] = max(b["hr_max"], d["hashrate"] or 0.0)
                kwh = d["watts"] * iv / 3_600_000
                b["kwh"] += kwh
                b["cost"] += kwh * d["tariff_ct"] / 100
            elif reach:
                b["paused_s"] += iv
            else:
                b["offline_s"] += iv
            st = "mint" if mining else ("pausiert" if reach else "nicht erreichbar")
            seg = segments.setdefault(d["device"], [])
            if seg and seg[-1][0] == st:
                seg[-1][2] = d["ts"]
                seg[-1][3] += iv
                seg[-1][4] += (d["hashrate"] or 0.0) * iv if mining else 0.0
            else:
                seg.append([st, d["ts"] - iv, d["ts"], iv, (d["hashrate"] or 0.0) * iv if mining else 0.0])
    else:
        s, e = hour_of(s), hour_of(e - 1) + HOUR  # auf volle Stunden
        for r in db.get().execute("SELECT * FROM activity_hourly WHERE hour >= ? AND hour < ?", (s, e)):
            b = buckets.setdefault((r["hour"], r["device"]), _empty())
            for k in ("polls", "mining_s", "paused_s", "offline_s", "hashes", "kwh"):
                b[k] += r[k]
            b["cost"] += r["cost_eur"]
            b["hr_max"] = max(b["hr_max"], r["hr_max"])

    # Erwartungswert je Stunde: Hashes / Difficulty x Blockbelohnung (nächstgelegener Netzwert)
    net = network.samples_between(s, e)
    for (hour, _dev), b in buckets.items():
        if b["hashes"] <= 0:
            continue
        n = network.nearest(net, hour + HOUR // 2)
        if n is None:
            b["exp_missing_s"] += b["mining_s"]
        else:
            b["exp_xmr"] += Decimal(b["hashes"]) / Decimal(n[1]) * Decimal(n[2]) / PICO

    devices: dict[str, dict] = {}
    days: dict[tuple[str, str], dict] = {}
    for (hour, dev), b in buckets.items():
        for agg in (devices.setdefault(dev, _empty()),
                    days.setdefault((datetime.fromtimestamp(hour, cfg.tz).date().isoformat(), dev), _empty())):
            for k in ("polls", "mining_s", "paused_s", "offline_s", "hashes", "kwh", "cost", "exp_xmr",
                      "exp_missing_s"):
                agg[k] += b[k]
            agg["hr_max"] = max(agg["hr_max"], b["hr_max"])
    for agg in list(devices.values()) + list(days.values()):
        agg["hr_avg"] = agg["hashes"] / agg["mining_s"] if agg["mining_s"] else 0.0

    total = _empty()
    for dev, agg in devices.items():
        keys = ("kwh", "cost") if dev == NAS_DEVICE else (
            "polls", "mining_s", "paused_s", "offline_s", "hashes", "kwh", "cost", "exp_xmr", "exp_missing_s")
        for k in keys:
            total[k] += agg[k]
        total["hr_max"] = max(total["hr_max"], agg["hr_max"])
    total["hr_avg"] = total["hashes"] / total["mining_s"] if total["mining_s"] else 0.0
    total["hr_eff"] = total["hashes"] / (e - s)   # über den ganzen Zeitraum gemittelt

    c = db.get()
    pr = c.execute("SELECT AVG(CAST(eur AS REAL)) AS a, COUNT(*) AS n FROM price_points WHERE ts >= ? AND ts < ?",
                   (s, e)).fetchone()
    price = Decimal(str(round(pr["a"], 4))) if pr["n"] else None
    if price is None:
        last = c.execute("SELECT eur FROM price_points WHERE ts < ? ORDER BY ts DESC LIMIT 1", (e,)).fetchone()
        price = Decimal(last["eur"]) if last else None

    payouts = [dict(r) for r in c.execute(
        "SELECT txid, height, ts, amount, price_eur FROM inflows WHERE kind='block' AND ts >= ? AND ts < ? ORDER BY ts",
        (s, e))]
    paid_xmr = Decimal(sum(p["amount"] for p in payouts)) / PICO
    paid_eur = sum((Decimal(p["amount"]) / PICO * Decimal(p["price_eur"]) for p in payouts if p["price_eur"]),
                   Decimal(0))

    in_range = [n for n in net if s <= n[0] < e]
    return {
        "start": datetime.fromtimestamp(s, cfg.tz), "end": datetime.fromtimestamp(e, cfg.tz),
        "resolution": "Minutenwerte" if minute else "Stundenwerte", "minute": minute,
        "devices": dict(sorted(devices.items())), "days": dict(sorted(days.items())), "total": total,
        "segments": segments,
        "price": price, "exp_eur": None if price is None else total["exp_xmr"] * price,
        "payouts": payouts, "paid_xmr": paid_xmr, "paid_eur": paid_eur,
        "luck": (paid_xmr / total["exp_xmr"]) if total["exp_xmr"] > 0 else None,
        "difficulty": (sum(n[1] for n in in_range) / len(in_range)) if in_range else None,
        "reward": (Decimal(sum(n[2] for n in in_range)) / len(in_range) / PICO) if in_range else None,
        "net_count": len(in_range),
    }
