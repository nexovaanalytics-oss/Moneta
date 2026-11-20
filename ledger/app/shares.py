# SPDX-License-Identifier: EUPL-1.2
"""Auszahlungen den Rechnern zuordnen.

P2Pool zahlt bei jedem Monero-Block, den der Pool findet, an alle Wallets mit Sidechain-Shares im
PPLNS-Fenster (2160 Sidechain-Blöcke), anteilig nach der Difficulty dieser Shares. Welcher Rechner eine
Share gefunden hat, steht nur im Log des eigenen P2Pool-Knotens:

  NOTICE  2026-11-14 03:12:45.1234 StratumServer SHARE FOUND: mainchain height 3806000, sidechain height
          11000000, diff 315000000, client 192.168.1.20:50123, user x, effort 87.123%
  NOTICE  2026-11-14 05:30:02.5678 P2Pool Your wallet 4… got a payout of 0.000312345678 XMR in block 3806070

Der Ledger liest dieses Log (im Compose-Stack nur lesend eingebunden) fortlaufend ein. Jede Auszahlung wird auf
die Rechner verteilt, deren Shares im Fenster davor lagen. Welcher Rechner eine Share gefunden hat, ergibt sich
in dieser Reihenfolge aus
  1. dem Login-Namen (XMRig -u = Gerätename) oder der Client-IP                         → „exakt“
  2. den Mining-Zeiten des Ledgers: minte zum Zeitpunkt nur ein Rechner, war er es        → „eindeutig“
  3. sonst anteilig nach der Hashrate der gleichzeitig minenden Rechner                  → „geschätzt“
P2Pool hinter dem Docker-Port-Proxy sieht oft nur die Gateway-Adresse; dann greifen 2. und 3.
Reicht das Log nicht so weit zurück oder fehlt es, wird nach dem Hash-Anteil der Rechner im Fenster verteilt
(„geschätzt“).

Reine Anzeige: Zuflüsse, Kurse, Bericht und Steuerwerte bleiben unverändert. Es geht nichts ins Internet.
"""
from __future__ import annotations

import json
import logging
import os
import time
import re
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlsplit

import activity
import db
import ledger
import miners
from config import Config

log = logging.getLogger("shares")

PPLNS_BLOCKS = 2160
BLOCK_TIME = {"mini": 10, "nano": 30, "main": 10}   # Sekunden je Sidechain-Block
LATE_S = 120          # Toleranz, wenn nur die Blockzeit (vom Finder gesetzt) bekannt ist
CHUNK = 4 * 1024 * 1024

# Kategoriale Farben in fester Reihenfolge (Farbe folgt dem Gerät, nicht dem Rang)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
UNKNOWN = "unbekannt"
UNKNOWN_COLOR = "#98a2b3"

_TS = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:\.\d+)?"
SHARE_RE = re.compile(_TS + r".*?SHARE FOUND: mainchain height (\d+), sidechain height (\d+), diff (\d+), "
                      r"client ([^,\s]+)(?:, user ([^,]*))?, effort ([\d.]+)%")
PAYOUT_RE = re.compile(_TS + r".*?Your wallet \S+ got a payout of (\d+)\.(\d{12}) XMR in block (\d+)")
TS_RE = re.compile(r"^\s*(?:NOTICE|WARNING|ERROR)?\s*" + _TS)


def _utc(s: str) -> int:
    """P2Pool schreibt die Zeit in UTC."""
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())


def host_of(client: str) -> str:
    """'192.168.1.20:50123' / '[::ffff:192.168.1.20]:50123' → '192.168.1.20'."""
    c = client.strip()
    if c.startswith("["):
        c = c[1:c.index("]")] if "]" in c else c[1:]
    elif c.count(":") == 1:
        c = c.split(":", 1)[0]
    if c.lower().startswith("::ffff:"):
        c = c[7:]
    return c


def parse_line(line: str) -> dict | None:
    m = SHARE_RE.search(line)
    if m:
        return {"kind": "share", "ts": _utc(m[1]), "mainchain_height": int(m[2]), "sidechain_height": int(m[3]),
                "difficulty": int(m[4]), "client": host_of(m[5]), "worker": (m[6] or "").strip() or None,
                "effort": float(m[7])}
    m = PAYOUT_RE.search(line)
    if m:
        return {"kind": "payout", "ts": _utc(m[1]), "amount": int(m[2]) * activity.PICO + int(m[3]),
                "height": int(m[4])}
    return None


# ---------- Geräte ----------
def device_names(cfg: Config) -> list[str]:
    """Alle bekannten Rechner in fester Reihenfolge: config.toml, dann gekoppelte (auch stillgelegte)."""
    names = [m.name for m in cfg.miners]
    for r in db.get().execute("SELECT name FROM devices ORDER BY id"):
        if r["name"] not in names:
            names.append(r["name"])
    return names


def colors(cfg: Config, extra=()) -> dict[str, str]:
    names = device_names(cfg)
    for n in extra:
        if n not in names and n not in (UNKNOWN, activity.NAS_DEVICE):
            names.append(n)
    out = {n: (SERIES[i] if i < len(SERIES) else UNKNOWN_COLOR) for i, n in enumerate(names)}
    out[UNKNOWN] = UNKNOWN_COLOR
    return out


def host_map(cfg: Config) -> dict[str, str]:
    """IP/Host → Gerätename. Aktive Rechner zuerst, danach stillgelegte (neueste zuerst)."""
    out: dict[str, str] = {}
    for m in miners.current(cfg):
        h = urlsplit(m.url).hostname
        if h:
            out.setdefault(h, m.name)
    for r in db.get().execute("SELECT name, url FROM devices ORDER BY id DESC"):
        h = urlsplit(r["url"]).hostname
        if h:
            out.setdefault(h, r["name"])
    return out


def p2pool_user(name: str) -> str:
    """So kürzt P2Pool einen Login zum „user“ im Log: bis zum ersten '+' oder '.', nur druckbares ASCII ohne
    Komma, Anführungszeichen und Backslash, höchstens 31 Zeichen (stratum_server.cpp, get_custom_user)."""
    out = []
    for ch in name:
        if ch in "+.":
            break
        if " " <= ch <= "~" and ch not in ',"\\':
            out.append(ch)
        if len(out) == 31:
            break
    return "".join(out).strip().lower()


def _resolver(cfg: Config):
    """resolve(worker, client) → (Gerät, 'login'|'ip') oder (None, None)."""
    hosts = host_map(cfg)
    names: dict[str, str] = {}
    for n in device_names(cfg):
        names.setdefault(p2pool_user(n), n)

    def resolve(worker: str | None, client: str) -> tuple[str | None, str | None]:
        w = p2pool_user(worker) if worker else ""
        if w and w != "x" and w in names:        # XMRig-Login = Gerätename (robust bei IP-Wechsel und Docker)
            return names[w], "login"
        if client in hosts:
            return hosts[client], "ip"
        return None, None
    return resolve


def active_weights(cfg: Config, ts: int) -> dict[str, float]:
    """Welche Rechner minten zum Zeitpunkt ts, mit welcher Hashrate? Aus den Minutenwerten (± 2 Abfragen),
    sonst aus den Stundenwerten der Stunde. NAS zählt nicht."""
    cap = 2 * cfg.poll_seconds
    acc: dict[str, list[float]] = {}
    for r in db.get().execute(
            "SELECT device, hashrate FROM power_samples WHERE ts >= ? AND ts <= ? AND mining = 1 AND hashrate > 0",
            (ts - cap, ts + cap)):
        if r["device"] != activity.NAS_DEVICE:
            acc.setdefault(r["device"], []).append(r["hashrate"])
    w = {d: sum(v) / len(v) for d, v in acc.items()}
    if not w:
        for r in db.get().execute("SELECT device, hashes FROM activity_hourly WHERE hour = ? AND hashes > 0",
                                  (activity.hour_of(ts),)):
            if r["device"] != activity.NAS_DEVICE:
                w[r["device"]] = r["hashes"] / activity.HOUR
    return w


def classify(cfg: Config, now: int | None = None) -> int:
    """Bestimmt für Shares ohne Herkunft das Gerät: Login/IP, sonst Mining-Zeiten (einziger Rechner → „allein“,
    mehrere → „anteilig“ mit Hashrate je Gerät). Wartet, bis die Minutenwerte um die Share vorliegen.
    Das Ergebnis wird gespeichert, weil Minutenwerte nach 30 Tagen gelöscht werden."""
    now = int(time.time()) if now is None else now
    settle = 2 * cfg.poll_seconds + 60
    c = db.get()
    rows = c.execute("SELECT rowid, ts, worker, client FROM p2pool_shares WHERE source IS NULL AND ts <= ?",
                     (now - settle,)).fetchall()
    if not rows:
        return 0
    resolve = _resolver(cfg)
    updates = []
    for r in rows:
        dev, how = resolve(r["worker"], r["client"])
        parts = None
        if not dev:
            w = active_weights(cfg, r["ts"])
            if len(w) == 1:
                dev, how = next(iter(w)), "allein"
            elif w:
                how, parts = "anteilig", json.dumps(w, ensure_ascii=False, sort_keys=True)
            else:
                how = "unbekannt"
        updates.append((dev, how, parts, r["rowid"]))
    with db.write_lock:
        c.executemany("UPDATE p2pool_shares SET device = ?, source = ?, parts = ? WHERE rowid = ?", updates)
        c.commit()
    return len(updates)


# ---------- Log einlesen ----------
def ingest(cfg: Config) -> int:
    """Liest neue Zeilen aus dem P2Pool-Log. Gibt die Zahl neu gespeicherter Shares und Auszahlungen zurück."""
    path = cfg.p2pool_log
    if not path:
        return 0
    try:
        st = os.stat(path)
    except OSError:
        if db.get_meta("p2pool_log_state") != "missing":
            log.info("P2Pool-Log %s nicht gefunden – Auszahlungen werden nur nach Hash-Anteil zugeordnet", path)
            db.set_meta("p2pool_log_state", "missing")
        return 0

    inode = str(st.st_ino)
    start = int(db.get_meta("p2pool_log_offset") or 0)
    if db.get_meta("p2pool_log_inode") != inode or st.st_size < start:
        start = 0                                   # neue, rotierte oder gekürzte Datei
    if start == st.st_size and db.get_meta("p2pool_log_state") == "ok":
        return 0

    resolve = _resolver(cfg)
    shares, payouts, first_ts, consumed = [], [], None, 0
    try:
        f = open(path, "rb")
    except PermissionError:
        if db.get_meta("p2pool_log_state") != "unreadable":
            log.warning("P2Pool-Log %s nicht lesbar (Rechte) – Auszahlungen werden nur nach Hash-Anteil zugeordnet",
                        path)
            db.set_meta("p2pool_log_state", "unreadable")
        return 0
    with f:
        f.seek(start)
        rest = b""
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            data = rest + chunk
            cut = data.rfind(b"\n")
            if cut < 0:
                rest = data
                continue
            lines, rest = data[:cut], data[cut + 1:]
            consumed += cut + 1
            for raw in lines.split(b"\n"):
                if start == 0 and first_ts is None:
                    m = TS_RE.match(raw.decode("utf-8", "replace"))
                    if m:
                        first_ts = _utc(m[1])
                if b"SHARE FOUND" not in raw and b"got a payout" not in raw:
                    continue
                p = parse_line(raw.decode("utf-8", "replace"))
                if p is None:
                    continue
                if p["kind"] == "share":
                    p["device"], p["source"] = resolve(p["worker"], p["client"])
                    shares.append(p)
                else:
                    payouts.append(p)

    with db.write_lock:
        c = db.get()
        n = 0
        for s in shares:
            n += c.execute(
                "INSERT OR IGNORE INTO p2pool_shares(ts, sidechain_height, mainchain_height, difficulty, client, "
                "worker, device, effort, source) VALUES(?,?,?,?,?,?,?,?,?)",
                (s["ts"], s["sidechain_height"], s["mainchain_height"], s["difficulty"], s["client"], s["worker"],
                 s["device"], s["effort"], s["source"])).rowcount
        for p in payouts:
            n += c.execute("INSERT OR IGNORE INTO p2pool_payouts(height, ts, amount) VALUES(?,?,?)",
                           (p["height"], p["ts"], p["amount"])).rowcount
        meta = {"p2pool_log_offset": str(start + consumed), "p2pool_log_inode": inode, "p2pool_log_state": "ok"}
        if first_ts is not None:
            old = db.get_meta("p2pool_log_since")
            meta["p2pool_log_since"] = str(min(first_ts, int(old)) if old else first_ts)
        for k, v in meta.items():
            c.execute("INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      (k, v))
        c.commit()
    if n:
        log.info("P2Pool-Log: %d neue Einträge (%d Shares, %d Auszahlungen)", n, len(shares), len(payouts))
    return n


def loop(cfg: Config, stop) -> None:
    while not stop.is_set():
        try:
            ingest(cfg)
            classify(cfg)
        except Exception:  # noqa: BLE001
            log.exception("P2Pool-Log: unerwarteter Fehler")
        stop.wait(60)


def log_state() -> tuple[str, int | None]:
    """('ok'|'missing'|'unreadable'|'', Beginn des Logs als Unix-Zeit)."""
    since = db.get_meta("p2pool_log_since")
    return db.get_meta("p2pool_log_state") or "", int(since) if since else None


# ---------- Zuordnung ----------
def window_s(cfg: Config) -> int:
    return PPLNS_BLOCKS * BLOCK_TIME.get(cfg.sidechain, 10)


SOURCE_RANK = {"login": 0, "ip": 0, "allein": 1, "anteilig": 2}


def shares_between(cfg: Config, a: int, b: int) -> list[dict]:
    """Eigene Shares mit a < ts <= b. Je Share: device (bei „anteilig“ das Gerät mit der höchsten Hashrate),
    split {Gerät: Anteil 0..1} und source. Noch nicht bestimmte Shares: Login/IP, sonst „unbekannt“."""
    resolve = _resolver(cfg)
    out = []
    for r in db.get().execute("SELECT * FROM p2pool_shares WHERE ts > ? AND ts <= ? ORDER BY ts", (a, b)):
        d = dict(r)
        w = json.loads(d["parts"]) if d["source"] == "anteilig" and d["parts"] else {}
        total = sum(w.values())
        if total > 0:
            d["split"] = {k: v / total for k, v in sorted(w.items(), key=lambda kv: -kv[1])}
            d["device"] = next(iter(d["split"]))
        else:
            if not d["device"]:
                d["device"], how = resolve(d["worker"], d["client"])
                if d["device"]:
                    d["source"] = how
            d["device"] = d["device"] or UNKNOWN
            d["split"] = {d["device"]: 1.0}
            if d["source"] == "anteilig":
                d["source"] = "unbekannt"
        out.append(d)
    return out


def hash_weights(a: int, b: int) -> dict[str, float]:
    """Hashes je Rechner im Zeitraum [a, b) aus den Stundenwerten (anteilig für angeschnittene Stunden)."""
    w: dict[str, float] = {}
    for r in db.get().execute(
            "SELECT hour, device, hashes FROM activity_hourly WHERE hour < ? AND hour + ? > ? AND hashes > 0",
            (b, activity.HOUR, a)):
        if r["device"] == activity.NAS_DEVICE:
            continue
        overlap = min(b, r["hour"] + activity.HOUR) - max(a, r["hour"])
        if overlap > 0:
            w[r["device"]] = w.get(r["device"], 0.0) + r["hashes"] * overlap / activity.HOUR
    return w


def split(amount: int, weights: dict) -> dict[str, int]:
    """Betrag (Piconero) nach Gewichten aufteilen; die Teile ergeben wieder genau den Betrag."""
    total = sum(weights.values())
    if total <= 0:
        return {}
    parts = {d: int(Decimal(amount) * Decimal(str(w)) / Decimal(str(total))) for d, w in weights.items()}
    rest = amount - sum(parts.values())
    if rest:
        top = max(weights, key=lambda d: weights[d])
        parts[top] += rest
    return dict(sorted(parts.items(), key=lambda kv: -kv[1]))


def attribute(cfg: Config, payouts: list[dict]) -> dict[str, dict]:
    """Ordnet Auszahlungen (Zeilen aus inflows: txid, height, ts, amount) den Rechnern zu.

    Ergebnis je txid: method („exakt“ = Login/IP, „eindeutig“ = nur ein Rechner minte zur Zeit der Share,
    „teilweise“ = Log beginnt im Fenster, „geschätzt“ = Hash-Anteil, „offen“),
    parts {Gerät: Piconero}, shares (die Shares im Fenster), ts (Zeitpunkt laut Log, sonst Blockzeit),
    window (Beginn, Ende)."""
    if not payouts:
        return {}
    c = db.get()
    win = window_s(cfg)
    _, since = log_state()
    heights = [p["height"] for p in payouts]
    logged: dict[int, int] = {}
    for i in range(0, len(heights), 500):
        part = heights[i:i + 500]
        q = f"SELECT height, ts FROM p2pool_payouts WHERE height IN ({','.join('?' * len(part))})"
        logged.update({r["height"]: r["ts"] for r in c.execute(q, part)})

    out: dict[str, dict] = {}
    for p in payouts:
        t = logged.get(p["height"], p["ts"])
        a = t - win
        sh = shares_between(cfg, a, t if p["height"] in logged else t + LATE_S)
        res = {"ts": t, "window": (a, t), "shares": sh, "parts": {}, "method": "offen"}
        if sh:
            weights: dict[str, Decimal] = {}
            for s in sh:
                for dev, f in s["split"].items():
                    weights[dev] = weights.get(dev, Decimal(0)) + Decimal(s["difficulty"]) * Decimal(str(f))
            res["parts"] = split(p["amount"], weights)
            rank = max(SOURCE_RANK.get(s["source"], 0) for s in sh)
            if rank == 2:
                res["method"] = "geschätzt"
            elif since is None or since > a:
                res["method"] = "teilweise"
            else:
                res["method"] = "eindeutig" if rank == 1 else "exakt"
        else:
            hw = hash_weights(a, t)
            if hw:
                res["parts"] = split(p["amount"], hw)
                res["method"] = "geschätzt"
        out[p["txid"]] = res
    return out


def by_device(payouts: list[dict], attr: dict[str, dict]) -> dict[str, dict]:
    """Summen je Rechner: zugeordnete Piconero (gesamt und exakt) und EUR-Gegenwert zum gespeicherten Kurs
    (je Anteil auf Cent gerundet). Nur Anzeige."""
    out: dict[str, dict] = {}
    for p in payouts:
        res = attr.get(p["txid"])
        if not res:
            continue
        price = Decimal(p["price_eur"]) if p.get("price_eur") else None
        for dev, pico in res["parts"].items():
            d = out.setdefault(dev, {"pico": 0, "exact": 0, "eur": Decimal(0), "payouts": 0})
            d["pico"] += pico
            d["payouts"] += 1
            if res["method"] in ("exakt", "eindeutig"):
                d["exact"] += pico
            if price is not None:
                d["eur"] += ledger.eur(ledger.xmr(pico) * price)
    return out
