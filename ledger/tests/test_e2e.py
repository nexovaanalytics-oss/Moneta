# SPDX-License-Identifier: EUPL-1.2
"""End-to-End-Test mit Fake-Wallet-RPC, Fake-XMRig und Fake-Kursen (ohne Internet).

Aufruf:  python ledger/tests/test_e2e.py      (oder: pytest ledger/tests)
"""
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
import urllib.request
from datetime import date, datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
sys.path.insert(0, os.path.abspath(APP))

TZ = ZoneInfo("Europe/Berlin")
ADDR = "4" + "A" * 94


def ts(*a):
    return int(datetime(*a, tzinfo=TZ).timestamp())


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def test_e2e():
    data = tempfile.mkdtemp(prefix="ledger-test-")
    try:
        _run(data)
    finally:
        shutil.rmtree(data, ignore_errors=True)


def _run(DATA):
    wallet_port, xmrig_port, web_port = free_port(), free_port(), free_port()

    transfers = [
        {"txid": "aa" * 32, "amount": 300_000_000, "height": 3805000, "timestamp": ts(2026, 11, 12, 10, 0), "type": "block"},
        {"txid": "bb" * 32, "amount": 250_000_000, "height": 3810000, "timestamp": ts(2026, 11, 20, 23, 30), "type": "block"},
        {"txid": "cc" * 32, "amount": 100_000_000, "height": 3840000, "timestamp": ts(2027, 1, 5, 8, 0), "type": "block"},
        {"txid": "cc" * 32, "amount": 50_000_000, "height": 3840000, "timestamp": ts(2027, 1, 5, 8, 0), "type": "block"},
        {"txid": "dd" * 32, "amount": 1_000_000_000, "height": 3841000, "timestamp": ts(2027, 1, 6, 9, 0), "type": "in"},
        {"txid": "ee" * 32, "amount": 400_000_000, "height": 3900000, "timestamp": ts(2027, 3, 1, 12, 0), "type": "block"},
    ]
    state = {"wallet_exists": False, "opened": False, "calls": []}

    class FakeWallet(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            m, p = req["method"], req.get("params", {})
            state["calls"].append(m)
            res, err = {}, None
            if m == "get_address":
                if state["opened"]:
                    res = {"address": ADDR}
                else:
                    err = {"code": -13, "message": "No wallet file"}
            elif m == "open_wallet":
                if state["wallet_exists"]:
                    state["opened"] = True
                else:
                    err = {"code": -1, "message": "Failed to open wallet"}
            elif m == "generate_from_keys":
                assert p["address"] == ADDR and p["viewkey"] == "f" * 64 and p["restore_height"] == 3500000
                state["wallet_exists"] = state["opened"] = True
                res = {"address": ADDR}
            elif m == "refresh":
                res = {"blocks_fetched": 10}
            elif m == "get_height":
                res = {"height": 3900100}
            elif m == "get_transfers":
                res = {"in": transfers}
            body = json.dumps({"jsonrpc": "2.0", "id": "0", **({"error": err} if err else {"result": res})}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    class FakeXmrig(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path != "/2/summary":
                self.send_response(404); self.end_headers(); return
            if self.headers.get("Authorization") != "Bearer tok123":
                self.send_response(401); self.end_headers(); return
            body = json.dumps({"paused": False, "uptime": 1234, "hashrate": {"total": [3806.2, 3790.0, None]},
                               "results": {"shares_good": 5}}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    for port, h in ((wallet_port, FakeWallet), (xmrig_port, FakeXmrig)):
        s = ThreadingHTTPServer(("127.0.0.1", port), h)
        threading.Thread(target=s.serve_forever, daemon=True).start()

    with open(f"{DATA}/config.toml", "w") as f:
        f.write(f"""
[general]
timezone = "Europe/Berlin"
data_dir = "{DATA}"

[wallet]
address = "{ADDR}"
view_key = "{'f' * 64}"
restore_height = 3500000
wallet_password = "pw"
rpc_url = "http://127.0.0.1:{wallet_port}/json_rpc"

[web]
port = {web_port}
user = "admin"
password = "geheim"

[power]
poll_seconds = 60
nas_extra_watts = 4.0
nas_note = "Schätzung"

[[power.tariff]]
valid_from = "2026-01-01"
ct_per_kwh = 35.0

[[power.tariff]]
valid_from = "2027-01-01"
ct_per_kwh = 30.0

[[miner]]
name = "MacBook Pro M3 Pro"
url = "http://127.0.0.1:{xmrig_port}"
token = "tok123"
watts = 12.0
note = "powermetrics +10 %"

[[miner]]
name = "MacBook Air M1"
url = "http://127.0.0.1:{free_port()}"
token = "x"
watts = 11.0
""")
    with open(f"{DATA}/kurse_manuell.csv", "w", encoding="utf-8") as f:
        f.write("# txid oder Datum;EUR\n" + "ee" * 32 + ";1.234,50\n")

    # --- Migration: alte DB (v1.0.0, user_version 0) muss ohne Datenverlust hochgezogen werden
    import db as dbmod
    old = sqlite3.connect(f"{DATA}/ledger.sqlite")
    old.executescript(dbmod.BASE_SCHEMA)
    old.execute("INSERT INTO meta(key,value) VALUES('alt','1')")
    old.commit()
    old.close()

    import config, db, ledger, miners, prices, report, walletsync, web  # noqa: E401

    cfg = config.load(f"{DATA}/config.toml")
    assert db.init(f"{DATA}/ledger.sqlite") == len(db.MIGRATIONS)
    assert db.get_meta("alt") == "1"

    # --- Kurse simulieren: lokale 5-Min-Historie für aa, cc (ee manuell), bb nur Tageskurs
    calls = []

    def fake_get(cfg_, path, params):
        calls.append((path, dict(params)))
        if path == "/coins/monero/market_chart":
            assert params == {"vs_currency": "eur", "days": "1"}, params  # keine Zeitpunkte an CoinGecko
            pts = []
            for t in (transfers[0]["timestamp"], transfers[2]["timestamp"]):
                pts += [[(t - 300) * 1000, 500.0], [(t + 120) * 1000, 512.3456], [(t + 420) * 1000, 530.0]]
            pts.append([(time.time() - 60) * 1000, 600.0])
            return {"prices": pts}
        if path == "/coins/monero/history":
            assert params["date"] == "20-11-2026", params
            return {"market_data": {"current_price": {"eur": 498.76}}}
        raise AssertionError(path)

    prices._get = fake_get
    real_sleep = time.sleep
    prices.time.sleep = lambda s: None

    # 1) Wallet-Sync (zweimal: Idempotenz)
    r = walletsync.sync_once(cfg)
    assert r["new"] == 5, r
    assert "generate_from_keys" in state["calls"]
    assert walletsync.sync_once(cfg)["new"] == 0
    assert db.get().execute("SELECT amount FROM inflows WHERE txid=?", ("cc" * 32,)).fetchone()["amount"] == 150_000_000

    # 2) Kurse
    assert prices.update_history(cfg) == 7
    assert prices.update_history(cfg) == 0  # keine Dubletten
    assert prices.current_price(cfg) == Decimal("600.0000")
    prices._now = lambda: ts(2028, 1, 1)  # alle Test-Zuflüsse liegen dann in der Vergangenheit
    assert prices.fill_missing(cfg) == 4
    rows = {r["txid"][:2]: r for r in db.get().execute("SELECT * FROM inflows")}
    assert rows["aa"]["price_eur"] == "512.3456" and "5-Min-Kurs (Abstand 2 Min.)" in rows["aa"]["price_source"]
    assert rows["bb"]["price_eur"] == "498.7600" and "Tageskurs 2026-11-20" in rows["bb"]["price_source"]
    assert rows["ee"]["price_eur"] == "1234.50" and "manuell" in rows["ee"]["price_source"]
    assert rows["dd"]["price_eur"] is None  # sonstiger Zugang: kein Kursabruf
    hist_dates = [p for p_, p in calls if p_ == "/coins/monero/history"]
    assert len(hist_dates) == 1  # nur für den Zufluss ohne lokalen Kurspunkt

    # 3) Miner-Abfrage: zwei Polls
    prices.time.sleep = real_sleep
    last = {}
    miners.poll_once(cfg, last)
    real_sleep(1.2)
    miners.poll_once(cfg, last)
    pd = {r["device"]: dict(r) for r in db.get().execute("SELECT * FROM power_daily")}
    pro = pd["MacBook Pro M3 Pro"]
    assert pro["mining_seconds"] >= 61, pd
    assert pd["MacBook Air M1"]["mining_seconds"] == 0
    assert "NAS (Node + Pool)" in pd
    exp_kwh = 12.0 * pro["mining_seconds"] / 3_600_000
    assert abs(pro["kwh"] - exp_kwh) < 1e-12 and abs(pro["cost_eur"] - exp_kwh * 0.35) < 1e-12
    assert miners.live_status()["MacBook Pro M3 Pro"]["mining"] is True
    assert miners.live_status()["MacBook Air M1"]["reachable"] is False
    dev = {p["device"]: p for p in ledger.power_by_device(cfg, datetime.now(TZ).year)}
    assert abs(dev["MacBook Pro M3 Pro"]["watts_eff"] - 12.0) < 1e-9
    assert abs(dev["MacBook Pro M3 Pro"]["tariff_eff"] - cfg.tariff_at(time.time())) < 1e-9

    # 4) Fristen
    assert ledger.steuerfrei_ab(date(2026, 11, 12)) == date(2027, 11, 13)
    assert ledger.steuerfrei_ab(date(2028, 2, 29)) == date(2029, 3, 1)
    assert ledger.steuerfrei_ab(date(2026, 12, 31)) == date(2028, 1, 1)

    # 5) Web
    srv = web.serve(cfg, threading.Event())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    auth = "Basic " + base64.b64encode(b"admin:geheim").decode()
    base = f"http://127.0.0.1:{web_port}"

    def http(path, data=None, with_auth=True, origin=base):
        req = urllib.request.Request(base + path, data=data)
        if with_auth:
            req.add_header("Authorization", auth)
        if origin:
            req.add_header("Origin", origin)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    assert http("/health", with_auth=False) == (200, b"ok")
    assert http("/", with_auth=False)[0] == 401
    assert http("/?jahr=abc")[0] == 400
    for p in ("/", "/?jahr=2026", "/zufluesse?jahr=2026", "/zufluesse?jahr=2027", "/strom", "/lose",
              "/abgaenge", "/rechner", "/rechner?menge=0,0005&datum=2027-06-01&kurs=600,00"):
        st, body = http(p)
        assert st == 200, (p, st, body[:300])
    assert b"Kursdaten: CoinGecko" in http("/")[1]

    # CSRF: POST von fremder Seite bzw. ohne Origin wird abgelehnt
    form = "datum=2027-06-01&uhrzeit=10:00&menge=0,0005&art=sale&erloes=310,00&txid=ff&notiz=Test".encode()
    assert http("/abgaenge", form, origin="http://evil.example")[0] == 403
    assert http("/abgaenge", form, origin=None)[0] == 403
    assert db.get().execute("SELECT COUNT(*) FROM disposals").fetchone()[0] == 0

    assert http("/abgaenge", form)[0] == 200
    assert http("/abgaenge", "datum=2027-12-02&menge=0.0001&art=own".encode())[0] == 200
    st, body = http("/abgaenge", "datum=2027-12-02&menge=0.0001&art=sale".encode())
    assert st == 400 and "Erlös" in body.decode()

    lots, disps = ledger.load_lots_and_disposals(cfg)
    sale = disps[0]
    assert [m.amount for m in sale.matches] == [300_000_000, 200_000_000]
    assert all(m.taxable for m in sale.matches)
    exp_cost = Decimal("0.0003") * Decimal("512.3456") + Decimal("0.0002") * Decimal("498.76")
    assert sum(m.cost for m in sale.matches) == exp_cost
    assert ledger.eur(sale.taxable_gain) == ledger.eur(Decimal("310") - exp_cost)
    own = disps[1]
    assert [(m.lot.txid[:2], m.amount) for m in own.matches] == [("bb", 50_000_000), ("cc", 50_000_000)]
    assert not any(m.taxable for m in own.matches)

    r = ledger.sale_calc(cfg, Decimal("0.0003"), date(2028, 3, 1), Decimal("600"))
    assert [(x["lot"].txid[:2], x["amount"], x["taxable"]) for x in r["rows"]] == [
        ("cc", 100_000_000, False), ("ee", 200_000_000, True)]

    # 6) Jahresübersicht: je Zufluss gerundet, dann summiert
    s = ledger.year_summary(cfg, 2026)
    exp_income = ledger.eur(Decimal("0.0003") * Decimal("512.3456")) + ledger.eur(Decimal("0.00025") * Decimal("498.76"))
    assert s["income"] == exp_income, (s["income"], exp_income)
    assert s["inflow_count"] == 2 and s["missing_prices"] == 0
    s27 = ledger.year_summary(cfg, 2027)
    assert s27["inflow_count"] == 2 and len(s27["other_inflows"]) == 1 and len(s27["disposals"]) == 2

    # 7) Downloads
    st, x = http("/bericht.xlsx?jahr=2027")
    assert st == 200 and x[:2] == b"PK"
    from openpyxl import load_workbook
    import io
    wb = load_workbook(io.BytesIO(x))
    assert wb.sheetnames == ["Übersicht", "Zuflüsse", "Strom", "Geräte", "Lose (Bestand)", "Abgänge",
                             "Sonstige Zugänge"]
    assert "XMR-Ledger" in wb["Übersicht"]["A2"].value
    st, c = http("/zufluesse.csv?jahr=2026")
    assert st == 200 and "512,3456" in c.decode("utf-8-sig")

    # 8) Reorg: Eintrag ee verschwindet -> wird entfernt
    transfers[:] = [t for t in transfers if t["txid"] != "ee" * 32]
    walletsync.sync_once(cfg)
    assert db.get().execute("SELECT COUNT(*) FROM inflows WHERE txid=?", ("ee" * 32,)).fetchone()[0] == 0

    srv.shutdown()


if __name__ == "__main__":
    test_e2e()
    print("ALLE TESTS OK")
