# SPDX-License-Identifier: EUPL-1.2
"""Kopplung neuer Rechner: Suche (/api/moneta), Code, /api/pair, Freigabe, Watt-Historie, Heartbeat,
Stilllegen, Excel-Bericht. Mit Fake-XMRig, ohne Internet."""
import base64
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
sys.path.insert(0, os.path.abspath(APP))


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def test_devices():
    data = tempfile.mkdtemp(prefix="ledger-devices-")
    try:
        _run(data)
    finally:
        import db
        db.close_thread()
        shutil.rmtree(data, ignore_errors=True)


def _run(DATA):
    xmrig_port, web_port = free_port(), free_port()

    class FakeXmrig(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.headers.get("Authorization") != "Bearer devtoken123":
                self.send_response(401)
                self.end_headers()
                return
            body = json.dumps({"paused": False, "hashrate": {"total": [3000.0, 2990.0, None]},
                               "results": {"shares_good": 3}, "uptime": 99}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    xs = ThreadingHTTPServer(("127.0.0.1", xmrig_port), FakeXmrig)
    threading.Thread(target=xs.serve_forever, daemon=True).start()

    with open(f"{DATA}/config.toml", "w") as f:
        f.write(f"""
[general]
data_dir = "{DATA}"
[wallet]
address = "4{'A' * 94}"
view_key = "{'f' * 64}"
restore_height = 1
wallet_password = "pw"
[web]
port = {web_port}
user = "admin"
password = "geheim"
[node]
rpc_url = ""
[pool]
stratum_port = 3334
[[power.tariff]]
valid_from = "2026-01-01"
ct_per_kwh = 30.0
[[miner]]
name = "Pro aus config"
url = "http://127.0.0.1:{free_port()}"
token = "x"
watts = 15.0
""")

    import config, db, devices, miners, report, web  # noqa: E401
    from openpyxl import load_workbook

    cfg = config.load(f"{DATA}/config.toml")
    assert cfg.stratum_port == 3334 and cfg.stratum_host == "" and cfg.pairing is True
    assert db.init(f"{DATA}/ledger.sqlite") == len(db.MIGRATIONS) >= 4
    devices.cancel_code()

    srv = web.serve(cfg, threading.Event())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{web_port}"
    auth = "Basic " + base64.b64encode(b"admin:geheim").decode()

    def http(path, data=None, headers=None, form=False):
        req = urllib.request.Request(base + path, data=data)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        if form:
            req.add_header("Authorization", auth)
            req.add_header("Origin", base)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def api(path, obj, token=None, ctype="application/json"):
        h = {"Content-Type": ctype}
        if token:
            h["Authorization"] = f"Bearer {token}"
        st, body = http(path, json.dumps(obj).encode(), h)
        return st, json.loads(body)

    # --- Suche: ohne Passwort, nichts Sensibles
    st, body = http("/api/moneta")
    disc = json.loads(body)
    assert st == 200 and disc["service"] == "moneta-ledger" and disc["stratum"] == {"host": None, "port": 3334}
    assert disc["pairing"] is True and "geheim" not in body.decode() and "f" * 64 not in body.decode()
    assert disc["economics"] is None  # noch kein Node-Wert und kein Kurs

    # Kennzahlen für einmessen.sh: Difficulty/Belohnung vom Node + lokaler Kurs + Tarif
    now = int(time.time())
    with db.write_lock:
        db.get().execute("INSERT INTO network_samples(height, ts, difficulty, reward) VALUES(?,?,?,?)",
                         (3_900_000, now - 600, 432_000_000_000, 600_000_000_000))
        db.get().execute("INSERT INTO price_points(ts, eur, source) VALUES(?,?,?)", (now - 300, "300.00", "test"))
        db.get().commit()
    eco = json.loads(http("/api/moneta")[1])["economics"]
    # 86.400 / 4,32e11 x 0,6 XMR x 300 € = 3,6e-5 € je H/s und Tag; 0,024 kWh x 0,30 € = 0,0072 € je W und Tag
    assert abs(eco["eur_per_hs_day"] - 3.6e-5) < 1e-12 and abs(eco["eur_per_w_day"] - 0.0072) < 1e-12
    assert eco["ct_per_kwh"] == 30.0 and eco["price_eur"] == 300.0 and eco["difficulty"] == 432_000_000_000

    pair_req = {"code": "000000", "name": "MacBook Air", "url": "http://192.168.1.20:18000",
                "token": "devtoken123", "threads": "3",
                "profile": {"model_name": "MacBook Air", "chip": "Apple M1", "fanless": True,
                            "cores": {"total": 8, "performance": 4, "efficiency": 4}},
                "proposal": {"threads": "3", "watts": 8.0, "note": "powermetrics 7,0 W - 0,4 W, +10 %"}}

    # --- Kopplung ohne Code bzw. mit falschem Format
    assert api("/api/pair", pair_req)[0] == 403                      # kein Code erzeugt
    assert api("/api/pair", pair_req, ctype="text/plain")[0] == 415  # kein Formular-CSRF
    assert http("/geraete/code", b"")[0] == 401                      # Dashboard nur mit Passwort
    assert http("/geraete/code", b"", {"Authorization": auth})[0] == 403  # … und nur vom Dashboard
    assert http("/geraete/code", b"", form=True)[0] == 200           # Redirect auf /geraete
    code = devices.active_code()["code"]
    assert code in http("/geraete", headers={"Authorization": auth})[1].decode().replace(" ", "")

    for bad in ({"url": "http://8.8.8.8:18000"}, {"url": "https://192.168.1.20:18000"}, {"url": "http://192.168.1.20"},
                {"token": "kurz"}, {"name": ""}, {"threads": "viele"}, {"name": "Pro aus config"},
                {"name": "NAS (Node + Pool)"}):
        st, res = api("/api/pair", {**pair_req, "code": code, **bad})
        assert st in (400, 409), (bad, st, res)
    assert devices.active_code()["code"] == code  # Formfehler verbrauchen den Code nicht

    # --- Fehlversuche: nach fünf ist der Code weg
    wrong = "111111" if code != "111111" else "222222"
    for _ in range(devices.MAX_FAILURES):
        assert api("/api/pair", {**pair_req, "code": wrong})[0] == 403
    assert devices.active_code() is None
    assert api("/api/pair", {**pair_req, "code": code})[0] == 403

    # --- Ablauf nach 10 Minuten
    old = devices.new_code(now=time.time() - devices.CODE_TTL - 1)
    assert api("/api/pair", {**pair_req, "code": old["code"]})[0] == 403

    # --- Erfolgreiche Kopplung → wartet auf Freigabe, wird noch nicht abgefragt
    code = devices.new_code()["code"]
    st, res = api("/api/pair", {**pair_req, "code": code})
    assert st == 201 and res["status"] == "pending" and res["stratum"]["port"] == 3334, res
    assert devices.active_code() is None  # einmalig
    assert devices.pending_count() == 1
    assert [m.name for m in miners.current(cfg)] == ["Pro aus config"]
    page_ = http("/geraete", headers={"Authorization": auth})[1].decode()
    assert "MacBook Air" in page_ and "Apple M1" in page_ and "lüfterlos" in page_ and "8,0" in page_
    assert "devtoken123" not in page_  # Token wird nie angezeigt
    assert "warten auf Freigabe" in http("/", headers={"Authorization": auth})[1].decode()

    # erneute Kopplung vor der Freigabe ersetzt die Anmeldung
    code = devices.new_code()["code"]
    assert api("/api/pair", {**pair_req, "code": code, "threads": "4"})[0] == 201
    pend = [d for d in devices.listing() if d["status"] == "pending"]
    assert len(pend) == 1 and pend[0]["threads"] == "4"
    dev_id = pend[0]["id"]

    # --- Freigabe: Watt und Notiz sind Pflicht
    st, body = http("/geraete/freigeben", f"id={dev_id}&watts=8,0&note=".encode(), form=True)
    assert st == 400 and "Notiz" in body.decode()
    st, body = http("/geraete/freigeben", f"id={dev_id}&watts=0&note=x".encode(), form=True)
    assert st == 400
    st, _ = http("/geraete/freigeben", f"id={dev_id}&watts=8,0&note=powermetrics+7,0+W".encode(), form=True)
    assert st == 200
    ms = {m.name: m for m in miners.current(cfg)}
    assert ms["MacBook Air"].watts == 8.0 and ms["MacBook Air"].source == "device"
    assert devices.pending_count() == 0
    # nach der Kopplung ist der Name belegt
    code = devices.new_code()["code"]
    assert api("/api/pair", {**pair_req, "code": code})[0] == 409
    devices.cancel_code()

    # --- Abfrage: Rechner zeigt im Test auf den Fake-XMRig (Loopback ist bei der Kopplung nicht erlaubt)
    with db.write_lock:
        db.get().execute("UPDATE devices SET url=? WHERE id=?", (f"http://127.0.0.1:{xmrig_port}", dev_id))
        db.get().commit()
    last = {}
    miners.poll_once(cfg, last)
    time.sleep(1.1)
    miners.poll_once(cfg, last)
    assert miners.live_status()["MacBook Air"]["mining"] is True
    rows = db.get().execute("SELECT watts, seconds FROM power_samples WHERE device='MacBook Air'").fetchall()
    assert len(rows) == 2 and all(r["watts"] == 8.0 for r in rows)
    live = json.loads(http("/api/live", headers={"Authorization": auth})[1])
    assert {m["name"] for m in live["miners"]} == {"Pro aus config", "MacBook Air"}
    assert live["totals"]["count"] == 2 and live["totals"]["mining"] == 1 and live["pending_devices"] == 0

    # --- Neuer Wert gilt ab jetzt, erfasste Abfragen behalten ihren Wert
    t_before = time.time()
    time.sleep(1.1)
    st, _ = http("/geraete/watt", f"id={dev_id}&watts=6,5&note=neu+gemessen+mit+3+Threads".encode(), form=True)
    assert st == 200
    assert devices.watts_at(dev_id, t_before)[0] == 8.0
    assert devices.watts_at(dev_id, time.time())[0] == 6.5
    miners.poll_once(cfg, last)
    ws = [r["watts"] for r in db.get().execute(
        "SELECT watts FROM power_samples WHERE device='MacBook Air' ORDER BY ts, rowid")]
    assert ws == [8.0, 8.0, 6.5]
    assert len(devices.listing()[0]["watts"]) == 2

    # --- Heartbeat: nur mit Geräte-Token; neue IP wird übernommen
    assert api("/api/heartbeat", {"url": "http://192.168.1.21:18000"})[0] == 401
    assert api("/api/heartbeat", {"url": "http://192.168.1.21:18000"}, token="falsch123")[0] == 401
    assert api("/api/heartbeat", {"url": "http://1.1.1.1:18000"}, token="devtoken123")[0] == 400
    st, res = api("/api/heartbeat", {"url": "http://192.168.1.21:18000", "threads": "3"}, token="devtoken123")
    assert st == 200 and res["status"] == "active" and res["url"] == "http://192.168.1.21:18000"
    d = devices.listing()[0]
    assert d["url"] == "http://192.168.1.21:18000" and d["threads"] == "3" and d["last_seen"] >= int(t_before)

    # --- Excel-Bericht: Watt-Historie mit „gültig ab“
    wb = load_workbook(BytesIO(report.build_xlsx(cfg, time.localtime().tm_year)))
    sheet = [[c.value for c in r] for r in wb["Geräte"].iter_rows(min_row=2, max_col=5)]
    air = [r for r in sheet if r[0] == "MacBook Air"]
    assert [r[1] for r in air] == [8.0, 6.5] and all(r[2] and r[4] == "gekoppelt" for r in air), sheet
    assert any(r[0] == "Pro aus config" and r[4] == "config.toml" for r in sheet)

    # --- Stilllegen: wird nicht mehr abgefragt, Historie bleibt, Name wieder frei
    assert http("/geraete/stilllegen", f"id={dev_id}".encode(), form=True)[0] == 200
    assert [m.name for m in miners.current(cfg)] == ["Pro aus config"]
    assert api("/api/heartbeat", {}, token="devtoken123")[0] == 401
    assert db.get().execute("SELECT COUNT(*) FROM device_watts WHERE device_id=?", (dev_id,)).fetchone()[0] == 2
    code = devices.new_code()["code"]
    st, res = api("/api/pair", {**pair_req, "code": code, "token": "neuestoken99"})
    assert st == 201, res
    new_id = res["id"]
    assert http("/geraete/ablehnen", f"id={new_id}".encode(), form=True)[0] == 200
    assert devices.pending_count() == 0
    assert "stillgelegt" in http("/geraete", headers={"Authorization": auth})[1].decode()

    # --- Kopplung abschaltbar
    cfg.pairing = False
    devices.new_code()
    assert api("/api/pair", {**pair_req, "code": devices.active_code()["code"]})[0] == 403
    assert json.loads(http("/api/moneta")[1])["pairing"] is False
    cfg.pairing = True
    devices.cancel_code()

    srv.shutdown()
    xs.shutdown()
