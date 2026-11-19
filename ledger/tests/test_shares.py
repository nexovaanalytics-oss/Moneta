# SPDX-License-Identifier: EUPL-1.2
"""Auszahlung → Rechner: P2Pool-Log einlesen (fortlaufend, gekürzte Datei), exakte Zuordnung nach
Share-Difficulty im PPLNS-Fenster, Schätzung nach Hash-Anteil, Web-Ausgabe. Ohne Internet."""
import base64
import os
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
sys.path.insert(0, os.path.abspath(APP))

PICO = 10 ** 12


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def utc(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def share_line(ts, diff, client, user="x", sidechain=11_000_000, prefix="NOTICE  "):
    return (f"{prefix}{utc(ts)}.1234 StratumServer SHARE FOUND: mainchain height 3806000, sidechain height "
            f"{sidechain}, diff {diff}, client {client}, user {user}, effort 87.123%\n")


def payout_line(ts, amount_pico, height):
    return (f"NOTICE  {utc(ts)}.5678 P2Pool Your wallet 4AbC...xYz got a payout of "
            f"{amount_pico // PICO}.{amount_pico % PICO:012d} XMR in block {height}\n")


def test_parse_line():
    import shares
    s = shares.parse_line(share_line(1_763_100_000, 315_000_000, "192.168.1.20:50123"))
    assert s == {"kind": "share", "ts": 1_763_100_000, "mainchain_height": 3806000, "sidechain_height": 11_000_000,
                 "difficulty": 315_000_000, "client": "192.168.1.20", "worker": "x", "effort": 87.123}
    # ohne Präfix (docker logs), IPv6-gemappte Adresse, ohne custom user
    line = (f"{utc(1_763_100_000)}.0001 StratumServer SHARE FOUND: mainchain height 1, sidechain height 2, "
            f"diff 3, client [::ffff:192.168.1.21]:4000, effort 1.5%")
    s2 = shares.parse_line(line)
    assert s2["client"] == "192.168.1.21" and s2["worker"] is None and s2["difficulty"] == 3
    p = shares.parse_line(payout_line(1_763_100_100, 312_345_678, 3806070))
    assert p == {"kind": "payout", "ts": 1_763_100_100, "amount": 312_345_678, "height": 3806070}
    assert shares.parse_line("NOTICE  2026-11-14 01:02:03.0000 P2Pool didn't get a payout in block 1") is None
    assert shares.host_of("[fe80::1]:3333") == "fe80::1"


def test_split():
    import shares
    parts = shares.split(1_000_000_001, {"A": 3, "B": 1})
    assert sum(parts.values()) == 1_000_000_001 and parts["A"] > parts["B"]
    assert list(parts) == ["A", "B"]
    assert shares.split(5, {}) == {} and shares.split(5, {"A": 0}) == {}


def test_attribution():
    data = tempfile.mkdtemp(prefix="ledger-shares-")
    try:
        _run(data)
    finally:
        import db
        db.close_thread()
        shutil.rmtree(data, ignore_errors=True)


def _run(DATA):
    web_port = free_port()
    logfile = f"{DATA}/p2pool.log"
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
rpc_url = ""

[pool]
log = "{logfile}"
sidechain = "mini"

[power]
poll_seconds = 60

[[power.tariff]]
valid_from = "2020-01-01"
ct_per_kwh = 30.0

[[miner]]
name = "Pro"
url = "http://192.168.1.20:18000"
watts = 15.0

[[miner]]
name = "Air"
url = "http://192.168.1.21:18000"
watts = 10.0
""")

    import activity, config, db, shares, web  # noqa: E401
    db.close_thread()
    cfg = config.load(f"{DATA}/config.toml")
    assert cfg.p2pool_log == logfile and shares.window_s(cfg) == 21600
    assert db.init(f"{DATA}/ledger.sqlite") == len(db.MIGRATIONS) >= 5

    now = int(datetime.now(timezone.utc).timestamp())
    h = activity.hour_of(now) - 30 * 3600
    log_start = h + 3600                      # Log beginnt hier
    T0 = log_start + 3600                     # Auszahlung, deren Fenster vor dem Log beginnt
    T1 = log_start + 8 * 3600                 # Pro + Air im Fenster
    T2 = log_start + 16 * 3600                # nur Air (custom user) im Fenster, Zeit laut Log
    T3 = log_start + 26 * 3600                # keine Share im Fenster → Schätzung

    # Ohne Log: nur Schätzung möglich, Hinweis im Zustand
    assert shares.ingest(cfg) == 0 and shares.log_state() == ("missing", None)

    lines = [
        f"NOTICE  {utc(log_start)}.0000 P2Pool started\n",
        share_line(log_start + 600, 300_000_000, "192.168.1.20:50001", sidechain=100),         # Pro, für T0
        share_line(T1 - 3 * 3600, 300_000_000, "192.168.1.20:50002", sidechain=200),           # Pro
        share_line(T1 - 3600, 100_000_000, "[::ffff:192.168.1.21]:50003", sidechain=300),      # Air
        "NOTICE  2026-11-14 01:02:03.0000 StratumServer irgendwas anderes\n",
        share_line(T2 - 600, 200_000_000, "10.9.9.9:50004", user="Air", sidechain=400),        # Air per Login-Name
        payout_line(T2 + 30, 50_000_000, 3_806_200),
    ]
    with open(logfile, "w") as f:
        f.writelines(lines)
    assert shares.ingest(cfg) == 5               # 4 Shares + 1 Auszahlung
    assert shares.ingest(cfg) == 0               # nichts Neues
    assert shares.log_state() == ("ok", log_start)
    stored = {r["sidechain_height"]: dict(r) for r in db.get().execute("SELECT * FROM p2pool_shares")}
    assert stored[300]["device"] == "Air" and stored[400]["device"] == "Air" and stored[200]["device"] == "Pro"

    # Weitere Zeile ohne Zeilenende wird erst gelesen, wenn sie vollständig ist
    with open(logfile, "a") as f:
        f.write(share_line(T3 + 7200, 100_000_000, "192.168.1.99:1", sidechain=500).rstrip("\n"))
    assert shares.ingest(cfg) == 0
    with open(logfile, "a") as f:
        f.write("\n")
    assert shares.ingest(cfg) == 1
    # Gekürzte/neue Datei: von vorn, ohne Doppelte
    with open(logfile, "w") as f:
        f.writelines(lines[:3])
    assert shares.ingest(cfg) == 0
    assert db.get().execute("SELECT COUNT(*) FROM p2pool_shares").fetchone()[0] == 5

    # Stundenwerte für die Schätzung (Fenster von T3): Pro 3.000 H/s, Air 1.000 H/s
    with db.write_lock:
        c = db.get()
        for k in range(6):
            hour = T3 - 6 * 3600 + k * 3600
            c.execute("INSERT INTO activity_hourly(hour, device, polls, mining_s, hashes) VALUES(?,?,?,?,?)",
                      (hour, "Pro", 60, 3600, 3000.0 * 3600))
            c.execute("INSERT INTO activity_hourly(hour, device, polls, mining_s, hashes) VALUES(?,?,?,?,?)",
                      (hour, "Air", 60, 3600, 1000.0 * 3600))
            c.execute("INSERT INTO activity_hourly(hour, device, polls, kwh) VALUES(?,?,?,?)",
                      (hour, activity.NAS_DEVICE, 60, 0.004))
        for i, (ts, amount, height) in enumerate([(T0, 10_000_000, 3_806_000), (T1, 40_000_000, 3_806_100),
                                                  (T2, 50_000_000, 3_806_200), (T3, 80_000_000, 3_806_300)]):
            c.execute("INSERT INTO inflows(txid, height, ts, amount, kind, price_eur, price_ts, price_source, "
                      "first_seen) VALUES(?,?,?,?,?,?,?,?,?)",
                      (f"tx{i}", height, ts, amount, "block", "400.00", ts, "test", ts))
        c.commit()

    pays = [dict(r) for r in db.get().execute("SELECT txid, height, ts, amount, price_eur FROM inflows ORDER BY ts")]
    attr = shares.attribute(cfg, pays)
    a0, a1, a2, a3 = (attr[f"tx{i}"] for i in range(4))
    assert a0["method"] == "teilweise" and a0["parts"] == {"Pro": 10_000_000}
    assert a1["method"] == "exakt" and a1["parts"] == {"Pro": 30_000_000, "Air": 10_000_000}
    assert len(a1["shares"]) == 2                   # die Share kurz nach Log-Beginn liegt außerhalb
    assert a2["method"] == "exakt" and a2["parts"] == {"Air": 50_000_000} and a2["ts"] == T2 + 30
    assert a3["method"] == "geschätzt" and a3["parts"] == {"Pro": 60_000_000, "Air": 20_000_000}
    tot = shares.by_device(pays, attr)
    assert tot["Pro"]["pico"] == 10_000_000 + 30_000_000 + 60_000_000 and tot["Pro"]["exact"] == 30_000_000
    assert tot["Air"]["payouts"] == 3

    # Web
    srv = web.serve(cfg, threading.Event())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    auth = "Basic " + base64.b64encode(b"admin:geheim").decode()

    def http(path):
        req = urllib.request.Request(f"http://127.0.0.1:{web_port}{path}")
        req.add_header("Authorization", auth)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    year = datetime.fromtimestamp(T1, cfg.tz).year
    st, page = http(f"/zufluesse?jahr={year}")
    assert st == 200 and "Verursacht von" in page and "Je Rechner" in page
    assert "Pro 75 % · Air 25 %" in page and ">exakt<" in page and ">geschätzt<" in page
    fmt = "%Y-%m-%dT%H:%M"
    q = urllib.parse.urlencode({"von": datetime.fromtimestamp(log_start, cfg.tz).strftime(fmt),
                                "bis": datetime.fromtimestamp(T3 + 3 * 3600, cfg.tz).strftime(fmt)})
    st, page = http(f"/auswertung?{q}")
    assert st == 200 and "Shares und Auszahlungen" in page and "<svg" in page and "<polygon" in page
    assert "zugeordnet XMR" in page and "unbekannt" in page   # Share von unbekannter IP hat eigene Spur
    srv.shutdown()
    srv.server_close()

    # Datei vorhanden, aber ohne Leserechte: eigener Zustand, kein Abbruch
    def denied(*a, **k):
        raise PermissionError(13, "Permission denied")
    with open(logfile, "a") as f:
        f.write(share_line(T3 + 7300, 100_000_000, "192.168.1.20:1", sidechain=600))
    shares.open = denied
    try:
        assert shares.ingest(cfg) == 0 and shares.log_state()[0] == "unreadable"
    finally:
        del shares.open

    # Ohne Log-Datei: Hinweis auf der Seite
    os.remove(logfile)
    shares.ingest(cfg)
    assert shares.log_state()[0] == "missing"
    srv = web.serve(cfg, threading.Event())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    assert "P2Pool-Log nicht eingebunden" in http(f"/auswertung?{q}")[1]
    srv.shutdown()
    srv.server_close()
