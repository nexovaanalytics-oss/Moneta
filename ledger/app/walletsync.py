# SPDX-License-Identifier: EUPL-1.2
"""Zuflüsse über monero-wallet-rpc (Nur-Lesen-Wallet) einlesen.

Hinweis: Eine Nur-Lesen-Wallet (View-Key) sieht alle Eingänge, aber keine
Ausgänge. Deshalb werden nur Coinbase-Eingänge (type 'block' = P2Pool-
Auszahlungen) als Mining-Zufluss gewertet. Sonstige Eingänge ('in', z. B.
Rückgeld eigener Überweisungen) werden gesondert gelistet, aber nicht als
Einnahme gezählt. Abgänge trägt man im Dashboard von Hand ein.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

import db
from config import Config

log = logging.getLogger("wallet")


class RpcError(Exception):
    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def rpc(cfg: Config, method: str, params: dict | None = None, timeout: int = 60):
    body = json.dumps({"jsonrpc": "2.0", "id": "0", "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(cfg.wallet_rpc_url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    if "error" in data:
        raise RpcError(data["error"].get("code"), data["error"].get("message", ""))
    return data.get("result", {})


def ensure_wallet_open(cfg: Config) -> None:
    """Öffnet die Nur-Lesen-Wallet; legt sie beim ersten Start aus Adresse + View-Key an."""
    try:
        addr = rpc(cfg, "get_address", {"account_index": 0})
        if addr.get("address") == cfg.address:
            return
    except RpcError:
        pass  # keine Wallet offen

    try:
        rpc(cfg, "open_wallet", {"filename": cfg.wallet_file, "password": cfg.wallet_password})
        log.info("Nur-Lesen-Wallet geöffnet")
        return
    except RpcError as e:
        log.info("Wallet nicht vorhanden (%s) – wird aus View-Key angelegt", e.message)

    rpc(cfg, "generate_from_keys", {
        "restore_height": cfg.restore_height,
        "filename": cfg.wallet_file,
        "address": cfg.address,
        "viewkey": cfg.view_key,
        "password": cfg.wallet_password,
        "autosave_current": True,
    }, timeout=120)
    log.info("Nur-Lesen-Wallet angelegt (Restore-Höhe %s)", cfg.restore_height)


def sync_once(cfg: Config) -> dict:
    ensure_wallet_open(cfg)
    rpc(cfg, "refresh", {}, timeout=1800)
    height = rpc(cfg, "get_height")["height"]
    res = rpc(cfg, "get_transfers", {"in": True, "out": False, "pending": False,
                                     "failed": False, "pool": False}, timeout=120)
    entries = res.get("in", [])

    # get_transfers kann mehrere Einträge je TXID liefern (z. B. Subadressen) -> zusammenfassen
    by_tx: dict[str, dict] = {}
    for e in entries:
        if not e.get("height"):
            continue
        t = by_tx.setdefault(e["txid"], {"txid": e["txid"], "height": int(e["height"]), "ts": int(e["timestamp"]),
                                        "amount": 0, "kind": "block" if e.get("type") == "block" else "in"})
        t["amount"] += int(e["amount"])

    now = db.now()
    new = 0
    with db.write_lock:
        c = db.get()
        for t in by_tx.values():
            cur = c.execute("SELECT amount, height FROM inflows WHERE txid=?", (t["txid"],)).fetchone()
            if cur is None:
                c.execute("INSERT INTO inflows(txid, height, ts, amount, kind, first_seen) VALUES(?,?,?,?,?,?)",
                          (t["txid"], t["height"], t["ts"], t["amount"], t["kind"], now))
                new += 1
            elif cur["amount"] != t["amount"] or cur["height"] != t["height"]:
                c.execute("UPDATE inflows SET amount=?, height=?, ts=? WHERE txid=?",
                          (t["amount"], t["height"], t["ts"], t["txid"]))
        # Durch Reorganisation verschwundene Einträge (nur jüngere Blöcke) entfernen
        gone = c.execute("SELECT txid, height FROM inflows WHERE height > ? AND height < ?",
                         (height - 720, height - 10)).fetchall()
        for g in gone:
            if g["txid"] not in by_tx:
                log.warning("Eingang %s (Block %s) nicht mehr in der Wallet – entfernt (Reorg)", g["txid"], g["height"])
                c.execute("DELETE FROM inflows WHERE txid=?", (g["txid"],))
        c.commit()

    db.set_meta("wallet_height", str(height))
    db.set_meta("wallet_last_sync", str(now))
    db.set_meta("wallet_error", "")
    if new:
        log.info("%d neue Eingänge, Wallet-Höhe %s", new, height)
    return {"height": height, "new": new}


def loop(cfg: Config, stop, interval: int = 120) -> None:
    while not stop.is_set():
        try:
            sync_once(cfg)
        except (urllib.error.URLError, TimeoutError, ConnectionError, RpcError, OSError) as e:
            msg = getattr(e, "message", None) or str(e)
            db.set_meta("wallet_error", msg)
            log.warning("Wallet-Sync fehlgeschlagen: %s", msg)
        except Exception as e:  # noqa: BLE001
            db.set_meta("wallet_error", repr(e))
            log.exception("Wallet-Sync: unerwarteter Fehler")
        stop.wait(interval)
