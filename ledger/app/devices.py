# SPDX-License-Identifier: EUPL-1.2
"""Gekoppelte Rechner: Kopplungscode, Anmeldung neuer Rechner, Freigabe, Watt-Historie, Heartbeat.

Ablauf: Im Dashboard wird ein Kopplungscode erzeugt (6 Ziffern, 10 Minuten gültig, einmalig).
Installer bzw. Menüleisten-App des Rechners senden damit POST /api/pair. Der Rechner steht dann als
„wartet auf Freigabe“ in der Liste; erst nach der Freigabe mit gemessenem Mehrverbrauch wird er
abgefragt und seine Mining-Zeit erfasst. Ein Gerät im LAN kann sich so nicht selbst in die
Stromkosten schreiben.

Watt werden nie überschrieben: jede Änderung ist eine neue Zeile mit valid_from = jetzt. Erfasst
wird – wie bei den Rechnern aus config.toml – der Wert, der zum Zeitpunkt der Abfrage gilt.
"""
from __future__ import annotations

import hmac
import ipaddress
import json
import re
import secrets
import threading
import time
import urllib.parse

import db
from activity import NAS_DEVICE
from config import Config, Miner

CODE_TTL = 10 * 60
MAX_FAILURES = 5          # danach ist der aktuelle Code verbraucht
MAX_BODY = 16 * 1024

_lock = threading.Lock()
_code: dict | None = None  # {"code": "123456", "expires": ts, "failures": n}

NAME_RE = re.compile(r"^[^\x00-\x1f<>]{1,64}$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9._~-]{8,128}$")
THREADS_RE = re.compile(r"^(all|[0-9]{1,3})$")


class PairError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


# ---------- Kopplungscode ----------
def new_code(now: float | None = None) -> dict:
    """Erzeugt einen neuen Code; ein vorheriger wird damit ungültig."""
    global _code
    now = now or time.time()
    with _lock:
        _code = {"code": f"{secrets.randbelow(1_000_000):06d}", "expires": int(now) + CODE_TTL, "failures": 0}
        return dict(_code)


def active_code(now: float | None = None) -> dict | None:
    now = now or time.time()
    with _lock:
        if _code and _code["expires"] > now:
            return dict(_code)
    return None


def cancel_code() -> None:
    global _code
    with _lock:
        _code = None


def _check_code(code: str, now: float) -> None:
    """Prüft den Code; bei Erfolg ist er verbraucht. Zu viele Fehlversuche machen ihn ungültig."""
    global _code
    with _lock:
        if not _code or _code["expires"] <= now:
            _code = None
            raise PairError(403, "Kein gültiger Kopplungscode – im Dashboard unter „Geräte“ einen neuen erzeugen")
        if not hmac.compare_digest(str(code).strip(), _code["code"]):
            _code["failures"] += 1
            if _code["failures"] >= MAX_FAILURES:
                _code = None
                raise PairError(403, "Kopplungscode falsch – zu viele Versuche, bitte einen neuen erzeugen")
            raise PairError(403, "Kopplungscode falsch")
        _code = None


# ---------- Prüfungen ----------
def validate_url(url: str) -> str:
    """Nur http zu einer Adresse im Heimnetz (private IPv4/IPv6 oder *.local) mit Port."""
    u = urllib.parse.urlparse(str(url).strip())
    if u.scheme != "http" or not u.hostname or not u.port or u.path not in ("", "/") or u.query or u.username:
        raise PairError(400, "url muss die Form http://<IP-des-Rechners>:<Port> haben")
    host = u.hostname
    if not host.endswith(".local"):
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            raise PairError(400, "url: IP-Adresse oder Name auf .local erwartet") from None
        if not ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            raise PairError(400, "url: nur Adressen im Heimnetz sind erlaubt")
    netloc = f"[{host}]:{u.port}" if ":" in host else f"{host}:{u.port}"
    return f"http://{netloc}"


def _validate_watts(watts, note) -> tuple[float, str]:
    try:
        w = float(str(watts).replace(",", "."))
    except ValueError:
        raise ValueError("Mehrverbrauch: Zahl in Watt angeben") from None
    if not 0 < w <= 2000:
        raise ValueError("Mehrverbrauch muss zwischen 0 und 2000 W liegen")
    note = str(note or "").strip()
    if not note:
        raise ValueError("Bitte im Feld „Notiz“ festhalten, wie der Wert gemessen wurde")
    return w, note[:500]


def _taken(cfg: Config, name: str, conn) -> str | None:
    if any(m.name == name for m in cfg.miners):
        return "config"
    row = conn.execute("SELECT status FROM devices WHERE name=? AND status != 'retired'", (name,)).fetchone()
    return row["status"] if row else None


# ---------- API für Rechner ----------
def pair(cfg: Config, body: dict, now: float | None = None) -> dict:
    """POST /api/pair – legt einen Rechner als „wartet auf Freigabe“ an."""
    now = now or time.time()
    if not cfg.pairing:
        raise PairError(403, "Kopplung ist in config.toml abgeschaltet ([pool] pairing = false)")
    if not isinstance(body, dict):
        raise PairError(400, "JSON-Objekt erwartet")
    name = str(body.get("name", "")).strip()
    token = str(body.get("token", "")).strip()
    threads = str(body.get("threads", "all")).strip() or "all"
    if not NAME_RE.match(name):
        raise PairError(400, "name fehlt oder ist ungültig (1–64 Zeichen)")
    if not TOKEN_RE.match(token):
        raise PairError(400, "token fehlt oder ist ungültig (8–128 Zeichen: A–Z a–z 0–9 . _ ~ -)")
    if not THREADS_RE.match(threads):
        raise PairError(400, "threads: Zahl oder all")
    url = validate_url(body.get("url", ""))
    profile = body.get("profile") or {}
    proposal = body.get("proposal") or {}
    if not isinstance(profile, dict) or not isinstance(proposal, dict):
        raise PairError(400, "profile und proposal müssen JSON-Objekte sein")
    stored_profile = json.dumps({"profile": profile, "proposal": proposal}, ensure_ascii=False)
    if len(stored_profile) > 8000:
        raise PairError(400, "profile/proposal zu groß")

    if name == NAS_DEVICE or _taken(cfg, name, db.get()) in ("config", "active"):
        raise PairError(409, f"Der Name „{name}“ ist schon vergeben – anderen Namen wählen oder "
                             f"das Gerät im Dashboard zuerst stilllegen")

    _check_code(body.get("code", ""), now)   # erst nach den Formprüfungen: Tippfehler kosten keinen Versuch

    with db.write_lock:
        c = db.get()
        taken = _taken(cfg, name, c)
        if taken in ("config", "active"):
            raise PairError(409, f"Der Name „{name}“ ist schon vergeben – anderen Namen wählen oder "
                                 f"das Gerät im Dashboard zuerst stilllegen")
        if taken == "pending":  # erneuter Versuch vor der Freigabe ersetzt die alte Anmeldung
            c.execute("DELETE FROM devices WHERE name=? AND status='pending'", (name,))
        cur = c.execute(
            "INSERT INTO devices(name, url, token, status, profile, threads, created, last_seen) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (name, url, token, "pending", stored_profile, threads, int(now), int(now)))
        c.commit()
    return {"status": "pending", "id": cur.lastrowid, "name": name,
            "message": "Gekoppelt – bitte im Dashboard unter „Geräte“ freigeben"}


def heartbeat(cfg: Config, token: str, body: dict, now: float | None = None) -> dict:
    """POST /api/heartbeat – der Rechner meldet sich mit seinem Token (Bearer) und ggf. neuer URL/Threads."""
    now = now or time.time()
    if not token:
        raise PairError(401, "Token fehlt")
    if not isinstance(body, dict):
        raise PairError(400, "JSON-Objekt erwartet")
    with db.write_lock:
        c = db.get()
        rows = c.execute("SELECT id, name, token, status, url, threads FROM devices "
                         "WHERE status IN ('pending', 'active')").fetchall()
        dev = next((r for r in rows if hmac.compare_digest(r["token"], token)), None)
        if dev is None:
            raise PairError(401, "Unbekanntes Token – Rechner neu koppeln")
        url = validate_url(body["url"]) if body.get("url") else dev["url"]
        threads = str(body.get("threads", dev["threads"] or "all")).strip()
        if not THREADS_RE.match(threads):
            raise PairError(400, "threads: Zahl oder all")
        c.execute("UPDATE devices SET url=?, threads=?, last_seen=? WHERE id=?", (url, threads, int(now), dev["id"]))
        c.commit()
    return {"status": dev["status"], "name": dev["name"], "url": url}


# ---------- Dashboard ----------
def approve(device_id: int, watts, note, now: float | None = None) -> None:
    now = int(now or time.time())
    w, note = _validate_watts(watts, note)
    with db.write_lock:
        c = db.get()
        row = c.execute("SELECT status FROM devices WHERE id=?", (device_id,)).fetchone()
        if not row or row["status"] != "pending":
            raise ValueError("Gerät wartet nicht (mehr) auf Freigabe")
        c.execute("UPDATE devices SET status='active', approved=? WHERE id=?", (now, device_id))
        c.execute("INSERT INTO device_watts(device_id, valid_from, watts, note, created) VALUES(?,?,?,?,?)",
                  (device_id, now, w, note, now))
        c.commit()


def reject(device_id: int) -> None:
    """Anmeldung verwerfen (nur solange noch nichts erfasst wurde, also im Status „pending“)."""
    with db.write_lock:
        c = db.get()
        c.execute("DELETE FROM devices WHERE id=? AND status='pending'", (device_id,))
        c.commit()


def set_watts(device_id: int, watts, note, now: float | None = None) -> None:
    """Neuer Mehrverbrauch ab jetzt; bereits erfasste Werte bleiben unverändert."""
    now = int(now or time.time())
    w, note = _validate_watts(watts, note)
    with db.write_lock:
        c = db.get()
        row = c.execute("SELECT status FROM devices WHERE id=?", (device_id,)).fetchone()
        if not row or row["status"] != "active":
            raise ValueError("Nur aktive Geräte können einen neuen Wert bekommen")
        last = c.execute("SELECT MAX(valid_from) FROM device_watts WHERE device_id=?", (device_id,)).fetchone()[0]
        valid_from = max(now, (last or 0) + 1)
        c.execute("INSERT INTO device_watts(device_id, valid_from, watts, note, created) VALUES(?,?,?,?,?)",
                  (device_id, valid_from, w, note, now))
        c.commit()


def retire(device_id: int, now: float | None = None) -> None:
    with db.write_lock:
        c = db.get()
        c.execute("UPDATE devices SET status='retired', retired=? WHERE id=? AND status='active'",
                  (int(now or time.time()), device_id))
        c.commit()


def watts_at(device_id: int, ts: float) -> tuple[float, str]:
    row = db.get().execute(
        "SELECT watts, note FROM device_watts WHERE device_id=? AND valid_from<=? ORDER BY valid_from DESC LIMIT 1",
        (device_id, int(ts))).fetchone()
    return (float(row["watts"]), row["note"]) if row else (0.0, "")


def active_miners(now: float | None = None) -> list[Miner]:
    now = now or time.time()
    out = []
    for r in db.get().execute("SELECT id, name, url, token FROM devices WHERE status='active' ORDER BY id"):
        w, note = watts_at(r["id"], now)
        out.append(Miner(name=r["name"], url=r["url"], token=r["token"], watts=w, note=note,
                         source="device", device_id=r["id"]))
    return out


def listing() -> list[dict]:
    """Alle gekoppelten Geräte (ohne Token) für das Dashboard."""
    out = []
    c = db.get()
    for r in c.execute("SELECT * FROM devices ORDER BY status='retired', created"):
        d = {k: r[k] for k in r.keys() if k != "token"}
        try:
            extra = json.loads(r["profile"] or "{}")
        except ValueError:
            extra = {}
        d["profile"] = extra.get("profile") or {}
        d["proposal"] = extra.get("proposal") or {}
        d["watts"] = [dict(w) for w in c.execute(
            "SELECT valid_from, watts, note FROM device_watts WHERE device_id=? ORDER BY valid_from", (r["id"],))]
        out.append(d)
    return out


def pending_count() -> int:
    return db.get().execute("SELECT COUNT(*) FROM devices WHERE status='pending'").fetchone()[0]
