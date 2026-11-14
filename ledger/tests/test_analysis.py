# SPDX-License-Identifier: EUPL-1.2
"""Seite „Auswertung“: Stundenwerte (inkl. Nachfüllen nach Migration 3), Difficulty vom Fake-Node,
Erwartungswert, Zeiträume und Web-Ausgabe. Ohne Internet."""
import base64
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
sys.path.insert(0, os.path.abspath(APP))

TZ = ZoneInfo("Europe/Berlin")
DIFF = 300_000_000_000
REWARD = 600_000_000_000  # 0,6 XMR


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def test_analysis():
    data = tempfile.mkdtemp(prefix="ledger-analysis-")
    try:
        _run(data)
    finally:
        import db
        db.close_thread()
        shutil.rmtree(data, ignore_errors=True)


def _run(DATA):
    node_port, web_port = free_port(), free_port()
    now = int(time.time())
    T0 = now - 20 * 86400           # Blockzeit von Höhe H0
    H0 = 3_800_000
    top = H0 + (now - T0) // 120
    calls = []

    class FakeNode(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            m, p = req["method"], req.get("params", {})
            calls.append((m, p))
            hdr = lambda h: {"height": h, "timestamp": T0 + (h - H0) * 120, "difficulty": DIFF, "reward": REWARD}  # noqa: E731
            if m == "get_info":
                res = {"height": top + 1}
            elif m == "get_last_block_header":
                res = {"block_header": hdr(top)}
            elif m == "get_block_headers_range":
                assert p["end_height"] - p["start_height"] < 1000  # Grenze des eingeschränkten RPC
                res = {"headers": [hdr(h) for h in range(p["start_height"], p["end_height"] + 1)]}
            else:
                res = None
            body = json.dumps({"jsonrpc": "2.0", "id": "0", "result": res}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    node = ThreadingHTTPServer(("127.0.0.1", node_port), FakeNode)
    threading.Thread(target=node.serve_forever, daemon=True).start()

    with open(f"{DATA}/config.toml", "w") as f:
        f.write(f"""
[general]
timezone = "Europe/Berlin"
data_dir = "{DATA}"

[wallet]
address = "4{'A' * 94}"
view_key = "{'f' * 64}"
restore_height = 1
wallet_password = "pw"

[web]
port = {web_port}
password = "geheim"

[node]
rpc_url = "http://127.0.0.1:{node_port}/json_rpc"

[power]
poll_seconds = 60
nas_extra_watts = 4.0

[[power.tariff]]
valid_from = "2020-01-01"
ct_per_kwh = 30.0

[[miner]]
name = "Pro"
url = "http://127.0.0.1:9"
watts = 12.0

[[miner]]
name = "Air"
url = "http://127.0.0.1:9"
watts = 10.0
""")

    import activity, config, db, miners, network, web  # noqa: E401
    db.close_thread()

    # Stand vor dem Update (Schema v2): zwei Stunden Minutenwerte, noch ohne Stundentabelle
    base = activity.hour_of(now) - 10 * 3600
    old = sqlite3.connect(f"{DATA}/ledger.sqlite")
    for sql in db.MIGRATIONS[:2]:
        old.executescript(sql)
    old.execute("PRAGMA user_version = 2")
    for i in range(120):
        ts = base + 60 + i * 60
        # Pro: 1. Stunde nicht erreichbar, 2. Stunde pausiert; Air: mint mit 1.000 H/s
        old.execute("INSERT INTO power_samples VALUES(?,?,?,?,?,?,?,?)", (ts, "Pro", int(i >= 60), 0, 0.0, 0, 12.0, 30.0))
        old.execute("INSERT INTO power_samples VALUES(?,?,?,?,?,?,?,?)", (ts, "Air", 1, 1, 1000.0, 60, 10.0, 30.0))
    old.commit()
    old.close()

    cfg = config.load(f"{DATA}/config.toml")
    assert cfg.node_rpc_url.endswith(f"{node_port}/json_rpc")
    assert db.init(f"{DATA}/ledger.sqlite") == len(db.MIGRATIONS) == 3
    assert activity.backfill_hourly(cfg) == 240
    assert activity.backfill_hourly(cfg) == 0  # nur einmal
    h = {(r["hour"], r["device"]): dict(r) for r in db.get().execute("SELECT * FROM activity_hourly")}
    assert h[(base, "Pro")]["offline_s"] == 3600 and h[(base + 3600, "Pro")]["paused_s"] == 3600
    assert h[(base, "Air")]["mining_s"] == 3600 and h[(base, "Air")]["hashes"] == 1000.0 * 3600

    # Nach dem Update: dritte Stunde live erfasst (Pro mint mit 3.000 H/s, Air weiter 1.000 H/s)
    for i in range(60):
        ts = base + 7200 + 60 + i * 60
        miners.record(cfg, "Pro", ts, True, True, 3000.0, 60, 12.0)
        miners.record(cfg, "Air", ts, True, True, 1000.0, 60, 10.0)
        miners.record(cfg, miners.NAS_DEVICE, ts, True, True, 0.0, 60, 4.0)
    h3 = {r["device"]: dict(r) for r in db.get().execute("SELECT * FROM activity_hourly WHERE hour=?", (base + 7200,))}
    assert h3["Pro"]["mining_s"] == 3600 and h3["Pro"]["hashes"] == 3000.0 * 3600 and h3["Pro"]["hr_max"] == 3000.0
    assert abs(h3["Pro"]["kwh"] - 0.012) < 1e-12 and abs(h3["Pro"]["cost_eur"] - 0.0036) < 1e-12

    # Difficulty vom Node: Nachholen ab den ältesten Minutenwerten, höchstens ein Wert je Stunde
    assert network.backfill(cfg, base) > 0
    assert all(p["end_height"] - p["start_height"] < 1000 for m, p in calls if m == "get_block_headers_range")
    per_hour = db.get().execute("SELECT ts - ts % 3600 AS h, COUNT(*) AS n FROM network_samples GROUP BY h").fetchall()
    assert per_hour and all(r["n"] == 1 for r in per_hour)
    assert network.backfill(cfg, base) == 0  # schon vorhanden
    network.sample_once(cfg)

    # Auswertung aus Minutenwerten
    start = datetime.fromtimestamp(base, TZ)
    end = start + timedelta(hours=3)
    a = activity.analyse(cfg, start, end)
    assert a["minute"] is True
    pro, air, t = a["devices"]["Pro"], a["devices"]["Air"], a["total"]
    assert (pro["offline_s"], pro["paused_s"], pro["mining_s"]) == (3600, 3600, 3600)
    assert air["mining_s"] == 10800 and air["hr_avg"] == 1000.0
    hashes = 3000.0 * 3600 + 1000.0 * 10800
    assert t["hashes"] == hashes and t["mining_s"] == 14400  # NAS zählt nicht bei der Zeit
    assert abs(t["kwh"] - (0.012 + 0.030 + 0.004)) < 1e-9  # Pro 1 h, Air 3 h, NAS 1 h
    exp = Decimal(hashes) / DIFF * REWARD / 10 ** 12
    assert abs(t["exp_xmr"] - exp) < Decimal("1e-15"), (t["exp_xmr"], exp)
    assert t["exp_missing_s"] == 0
    segs = a["segments"]["Pro"]
    assert [s[0] for s in segs] == ["nicht erreichbar", "pausiert", "mint"]
    assert a["difficulty"] == DIFF and a["reward"] == Decimal("0.6")

    # Gleiches Ergebnis aus Stundenwerten, wenn die Minutenwerte gelöscht sind (30-Tage-Grenze)
    with db.write_lock:
        db.get().execute("DELETE FROM power_samples")
        db.get().commit()
    b = activity.analyse(cfg, start, end)
    assert b["minute"] is False and b["segments"] == {}
    assert b["total"]["hashes"] == hashes and b["devices"]["Pro"]["paused_s"] == 3600
    assert abs(b["total"]["exp_xmr"] - exp) < Decimal("1e-15")

    # Zeiträume
    n = datetime(2026, 11, 14, 6, 30, tzinfo=TZ)
    assert activity.preset_range(cfg, "nacht", n) == (datetime(2026, 11, 13, 18, 0, tzinfo=TZ), n)
    n2 = datetime(2026, 11, 14, 12, 0, tzinfo=TZ)
    assert activity.preset_range(cfg, "nacht", n2)[1] == datetime(2026, 11, 14, 8, 0, tzinfo=TZ)
    assert activity.preset_range(cfg, "monat", n2)[0] == datetime(2026, 11, 1, tzinfo=TZ)

    # Web
    srv = web.serve(cfg, threading.Event())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    auth = "Basic " + base64.b64encode(b"admin:geheim").decode()

    def http(path):
        req = urllib.request.Request(f"http://127.0.0.1:{web_port}{path}")
        req.add_header("Authorization", auth)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    q = urllib.parse.urlencode({"von": start.strftime("%Y-%m-%dT%H:%M"), "bis": end.strftime("%Y-%m-%dT%H:%M")})
    st, body = http(f"/auswertung?{q}")
    page = body.decode()
    assert st == 200 and "Je Gerät" in page and "Gesamt" in page and "Rechnerischer Gegenwert" in page
    assert "Stundenwerte" in page and "300,0 G" in page
    for k in ("nacht", "24h", "7d", "30d", "monat", "jahr"):
        assert http(f"/auswertung?zeitraum={k}")[0] == 200, k
    assert "Ungültiger Zeitraum" in http("/auswertung?zeitraum=xyz")[1].decode()
    assert "Ungültiger Zeitraum" in http(f"/auswertung?von={start.strftime('%Y-%m-%dT%H:%M')}&bis=2000-01-01T00:00")[1].decode()
    st, c = http(f"/auswertung.csv?{q}")
    csv_text = c.decode("utf-8-sig")
    assert st == 200 and csv_text.startswith("Tag;Gerät;Mining h") and ";Pro;" in csv_text
    assert http("/auswertung.csv?zeitraum=xyz")[0] == 400
    assert b"/auswertung" in http("/")[1]  # Navigation
    srv.shutdown()
    node.shutdown()
