# SPDX-License-Identifier: EUPL-1.2
"""Dashboard, Formulare und Downloads (nur im Heimnetz, mit Passwort)."""
from __future__ import annotations

import base64
import csv
import hmac
import html
import io
import json
import logging
import urllib.parse
from datetime import date, datetime, time as dtime, timedelta
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import activity
import db
import ledger
import miners
import prices
import report
import version
from config import Config

log = logging.getLogger("web")
CFG: Config | None = None


# ---------- Formatierung ----------
def de(v, digits=2) -> str:
    if v is None:
        return "–"
    s = f"{float(v):,.{digits}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def eurf(v) -> str:
    return "–" if v is None else f"{de(v)} €"


def xmrf(pico: int | None, digits=6) -> str:
    return "–" if pico is None else de(ledger.xmr(pico), digits)


def dfmt(d: date | None) -> str:
    return "–" if d is None else d.strftime("%d.%m.%Y")


def tsfmt(ts: int | float | None) -> str:
    if not ts:
        return "–"
    return datetime.fromtimestamp(float(ts), CFG.tz).strftime("%d.%m.%Y %H:%M")


def esc(s) -> str:
    return html.escape(str(s))


def parse_dec(s: str) -> Decimal:
    s = (s or "").strip().replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return Decimal(s)


CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2430;--mut:#667085;--line:#e4e7ec;--acc:#f26822;--ok:#12805c;--warn:#b54708;--bad:#b42318}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink)}
header{background:#1d2430;color:#fff;padding:14px 24px;display:flex;gap:24px;align-items:center;flex-wrap:wrap}
header b{font-size:17px}header a{color:#cfd6e4;text-decoration:none}header a.on,header a:hover{color:#fff}
main{max-width:1180px;margin:0 auto;padding:22px}
h1{font-size:22px;margin:4px 0 16px}h2{font-size:16px;margin:26px 0 10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card .k{color:var(--mut);font-size:13px}.card .v{font-size:22px;font-weight:600;margin-top:4px;font-variant-numeric:tabular-nums}
.card .s{color:var(--mut);font-size:12.5px;margin-top:4px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;font-size:13.5px;vertical-align:top}
th{background:#f0f2f5;font-weight:600}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:12px}.mut{color:var(--mut)}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}
.pill{display:inline-block;padding:2px 8px;border-radius:99px;font-size:12px;font-weight:600}
.pill.ok{background:#e7f6ef}.pill.warn{background:#fef0e6}.pill.bad{background:#fdecea}.pill.mut{background:#eef0f3}
form.inline{display:flex;gap:10px;flex-wrap:wrap;align-items:end;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
label{display:flex;flex-direction:column;font-size:12.5px;color:var(--mut);gap:4px}
input,select{font:inherit;padding:7px 9px;border:1px solid #cfd4dc;border-radius:7px;min-width:120px}
button,.btn{font:inherit;background:var(--acc);color:#fff;border:0;border-radius:7px;padding:8px 14px;cursor:pointer;text-decoration:none;display:inline-block}
button.sec{background:#eef0f3;color:var(--ink)}footer{margin-top:40px;color:var(--mut);font-size:12px}.note{background:#fff8e6;border:1px solid #f5d77a;border-radius:10px;padding:10px 14px;font-size:13.5px}
"""

NAV = [("/", "Übersicht"), ("/zufluesse", "Zuflüsse"), ("/strom", "Strom"), ("/auswertung", "Auswertung"),
       ("/lose", "Lose"),
       ("/abgaenge", "Abgänge"), ("/rechner", "Verkaufs-Rechner")]


def page(path: str, title: str, body: str, refresh: int | None = None) -> str:
    nav = "".join(f'<a href="{h}" class="{"on" if h == path else ""}">{esc(t)}</a>' for h, t in NAV)
    # Rückfall ohne JavaScript; mit JavaScript aktualisiert /api/live die Übersicht ohne Neuladen.
    meta = f'<noscript><meta http-equiv="refresh" content="{refresh}"></noscript>' if refresh else ""
    return (f'<!doctype html><html lang="de"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">{meta}'
            f'<title>{esc(title)} – XMR-Ledger</title><style>{CSS}</style></head><body>'
            f'<header><b>XMR-Ledger</b>{nav}</header><main>{body}'
            f'<footer>{esc(version.label())} · Kursdaten: CoinGecko</footer></main></body></html>')


def year_select(path: str, year: int) -> str:
    c = db.get()
    years = {datetime.now(CFG.tz).year}
    for r in c.execute("SELECT DISTINCT ts FROM inflows"):
        years.add(datetime.fromtimestamp(r["ts"], CFG.tz).year)
    for r in c.execute("SELECT DISTINCT substr(day,1,4) AS y FROM power_daily"):
        years.add(int(r["y"]))
    opts = "".join(f'<option value="{y}" {"selected" if y == year else ""}>{y}</option>' for y in sorted(years))
    return (f'<form class="inline" method="get" action="{path}" style="padding:8px 12px;display:inline-flex">'
            f'<label>Jahr<select name="jahr" onchange="this.form.submit()">{opts}</select></label></form>')


# ---------- Seiten ----------
LIVE_SECONDS = 30  # Abfrageintervall des Browsers für /api/live

LIVE_JS = """
(function(){
  var ms=%d, url='/api/live'+location.search, last=Date.now(), ok=true, busy=false, timer=null;
  var st=document.getElementById('live-state');
  function show(){
    var s=Math.round((Date.now()-last)/1000);
    st.className='pill '+(ok?'ok':'bad');
    st.textContent=(ok?'live':'Verbindung verloren')+' · Stand vor '+(s<60?s+' s':Math.round(s/60)+' Min.');
  }
  function tick(){
    if(busy)return; busy=true;
    var ac=new AbortController(), to=setTimeout(function(){ac.abort();},10000);
    fetch(url,{credentials:'same-origin',cache:'no-store',signal:ac.signal})
      .then(function(r){if(!r.ok)throw new Error(r.status);return r.json();})
      .then(function(d){
        Object.keys(d.html).forEach(function(k){
          var el=document.querySelector('[data-live="'+k+'"]'); if(el)el.innerHTML=d.html[k];
        });
        last=Date.now(); ok=true;
      })
      .catch(function(){ok=false;})
      .then(function(){clearTimeout(to); busy=false; show();});
  }
  function start(){if(!timer){tick(); timer=setInterval(tick,ms);}}
  function stop(){clearInterval(timer); timer=null;}
  document.addEventListener('visibilitychange',function(){document.hidden?stop():start();});
  setInterval(show,5000); show();
  if(!document.hidden)timer=setInterval(tick,ms);
})();
"""


def _ov_warn(s) -> str:
    if not s["missing_prices"]:
        return ""
    return (f'<p class="note">{s["missing_prices"]} Zufluss/Zuflüsse ohne Kurs – wird automatisch nachgeholt; '
            f'sonst in <span class="mono">kurse_manuell.csv</span> eintragen.</p>')


def _ov_cards(year: int, s, h, cur) -> str:
    price, price_ts = cur if cur else (None, None)
    value_now = None if price is None else ledger.xmr(h["remaining"]) * price
    fg = ('<span class="pill ok">unter 256 €</span>' if s["under_freigrenze_22"]
          else '<span class="pill warn">über 256 €</span>')
    stand = f"Stand {datetime.fromtimestamp(price_ts, CFG.tz).strftime('%H:%M')}" if price_ts else "kein aktueller Kurs"
    return f"""
      <div class="card"><div class="k">Bestand (Mining-Lose)</div><div class="v">{xmrf(h['remaining'])} XMR</div>
        <div class="s">aktuell ≈ {eurf(None if value_now is None else ledger.eur(value_now))} · AK {eurf(h['cost'])}</div></div>
      <div class="card"><div class="k">davon steuerfrei veräußerbar</div><div class="v">{xmrf(h['free_now'])} XMR</div>
        <div class="s">nächste Freigabe: {dfmt(h['next_free'])}</div></div>
      <div class="card"><div class="k">Einnahmen {year}</div><div class="v">{eurf(s['income'])}</div>
        <div class="s">{s['inflow_count']} Auszahlungen · {xmrf(s['inflow_amount'])} XMR</div></div>
      <div class="card"><div class="k">Stromkosten {year}</div><div class="v">{eurf(s['power_cost'])}</div>
        <div class="s">{de(s['power_kwh'], 1)} kWh</div></div>
      <div class="card"><div class="k">Ergebnis {year} (Einnahmen − Strom)</div><div class="v">{eurf(s['result'])}</div>
        <div class="s">Freigrenze: {fg}</div></div>
      <div class="card"><div class="k">XMR-Kurs aktuell</div><div class="v">{eurf(price)}</div>
        <div class="s">CoinGecko, {stand}</div></div>"""


def _ov_sync() -> str:
    werr = db.get_meta("wallet_error") or ""
    wsync = db.get_meta("wallet_last_sync")
    wheight = db.get_meta("wallet_height")
    return (f'<span class="pill bad">Fehler</span> <span class="mut">{esc(werr)}</span>' if werr else
            f'<span class="pill ok">OK</span> Block {de(int(wheight), 0) if wheight else "–"}, '
            f'zuletzt {tsfmt(wsync)}' if wsync else '<span class="pill mut">noch kein Abgleich</span>')


def _ov_devices(live) -> str:
    rows = ""
    for m in CFG.miners:
        st = live.get(m.name)
        if not st:
            state = '<span class="pill mut">noch keine Abfrage</span>'
        elif st["mining"]:
            state = '<span class="pill ok">mint</span>'
        elif st["reachable"]:
            state = '<span class="pill warn">pausiert</span>'
        else:
            state = '<span class="pill mut">nicht erreichbar</span>'
        rows += (f"<tr><td>{esc(m.name)}</td><td>{state}</td>"
                 f"<td class='n'>{de(st['hashrate'], 0) if st else '–'} H/s</td>"
                 f"<td class='n'>{de(m.watts, 1)} W</td><td class='mut'>{tsfmt(st['ts']) if st else '–'}</td></tr>")
    t = device_totals(live)
    total = ""
    if CFG.miners:
        nas = f"inkl. NAS {de(CFG.nas_extra_watts, 1)} W" if CFG.nas_extra_watts > 0 else ""
        total = (f"<tr style='font-weight:600;background:#f0f2f5'><td>Gesamt</td>"
                 f"<td>{t['mining']} von {t['count']} minen</td>"
                 f"<td class='n'>{de(t['hashrate'], 0)} H/s</td><td class='n'>{de(t['watts'], 1)} W</td>"
                 f"<td class='mut' style='font-weight:400'>{nas}</td></tr>")
    return (f"<tr><th>Gerät</th><th>Status</th><th class='n'>Hashrate</th>"
            f"<th class='n'>Mehrverbrauch</th><th>letzte Abfrage</th></tr>"
            f"{rows or '<tr><td colspan=5 class=mut>Keine Rechner in config.toml</td></tr>'}{total}")


def device_totals(live) -> dict:
    """Summe über alle Rechner: Hashrate und Mehrverbrauch der gerade minenden Geräte (+ NAS, falls angesetzt)."""
    active = [m for m in CFG.miners if (live.get(m.name) or {}).get("mining")]
    return {"count": len(CFG.miners), "mining": len(active),
            "hashrate": sum(live[m.name]["hashrate"] or 0.0 for m in active),
            "watts": sum(m.watts for m in active) + max(CFG.nas_extra_watts, 0.0)}


def _ov_recent(s) -> str:
    last = s["inflows"][-12:][::-1]
    inrows = "".join(
        f"<tr><td>{x['dt'].strftime('%d.%m.%Y %H:%M')}</td><td class='n'>{x['height']}</td>"
        f"<td class='n'>{xmrf(x['amount'], 8)}</td><td class='n'>{eurf(x['price'])}</td>"
        f"<td class='n'>{eurf(None if x['value'] is None else ledger.eur(x['value']))}</td></tr>" for x in last)
    return (f"<tr><th>Zeit</th><th class='n'>Block</th><th class='n'>XMR</th>"
            f"<th class='n'>Kurs</th><th class='n'>Wert</th></tr>"
            f"{inrows or '<tr><td colspan=5 class=mut>Noch keine Auszahlungen</td></tr>'}")


def overview_live(year: int) -> dict:
    """Daten der Übersicht für das Live-Update (/api/live): Rohwerte plus fertige HTML-Teile."""
    s = ledger.year_summary(CFG, year)
    h = ledger.holdings(CFG)
    cur = prices.current_price_point(CFG)
    live = miners.live_status()
    wh = db.get_meta("wallet_height")
    ws = db.get_meta("wallet_last_sync")
    return {
        "now": int(datetime.now(CFG.tz).timestamp()),
        "version": version.label(),
        "price": None if cur is None else {"eur": str(cur[0]), "ts": cur[1]},
        "wallet": {"height": int(wh) if wh else None, "last_sync": int(float(ws)) if ws else None,
                   "error": db.get_meta("wallet_error") or None},
        "miners": [{"name": m.name, "reachable": (live.get(m.name) or {}).get("reachable"),
                    "mining": (live.get(m.name) or {}).get("mining"),
                    "hashrate": (live.get(m.name) or {}).get("hashrate"),
                    "ts": (live.get(m.name) or {}).get("ts")} for m in CFG.miners],
        "totals": device_totals(live),
        "html": {"warn": _ov_warn(s), "cards": _ov_cards(year, s, h, cur), "sync": _ov_sync(),
                 "devices": _ov_devices(live), "recent": _ov_recent(s)},
    }


def p_overview(q) -> str:
    year = int(q.get("jahr", [datetime.now(CFG.tz).year])[0])
    d = overview_live(year)["html"]
    body = (f"<h1>Übersicht {year_select('/', year)} <span id='live-state' class='pill mut' "
            f"style='vertical-align:middle'>Live-Update aus</span></h1>"
            f"<div data-live='warn'>{d['warn']}</div><div class='grid' data-live='cards'>{d['cards']}</div>"
            f"<h2>Wallet-Abgleich</h2><p data-live='sync'>{d['sync']}</p>"
            f"<h2>Geräte</h2><table data-live='devices'>{d['devices']}</table>"
            f"<h2>Letzte Auszahlungen</h2><table data-live='recent'>{d['recent']}</table>"
            f'<h2>Jahresbericht</h2><p><a class="btn" href="/bericht.xlsx?jahr={year}">Excel-Bericht {year}</a> '
            f'<a class="btn" style="background:#475467" href="/zufluesse.csv?jahr={year}">Zuflüsse als CSV</a></p>'
            f"<script>{LIVE_JS % (LIVE_SECONDS * 1000)}</script>")
    return page("/", "Übersicht", body, refresh=120)


def p_inflows(q) -> str:
    year = int(q.get("jahr", [datetime.now(CFG.tz).year])[0])
    rows = ledger.inflows_in_year(CFG, year)
    tr = "".join(
        f"<tr><td>{x['dt'].strftime('%d.%m.%Y %H:%M:%S')}</td><td class='n'>{x['height']}</td>"
        f"<td class='mono'>{esc(x['txid'])}</td><td class='n'>{xmrf(x['amount'], 12)}</td>"
        f"<td class='n'>{eurf(x['price'])}</td><td class='n'>{eurf(None if x['value'] is None else ledger.eur(x['value']))}</td>"
        f"<td class='mut'>{esc(x['source']) or '<span class=bad>Kurs fehlt</span>'}</td></tr>" for x in rows)
    other = ledger.inflows_in_year(CFG, year, kind="in")
    tr2 = "".join(
        f"<tr><td>{x['dt'].strftime('%d.%m.%Y %H:%M')}</td><td class='n'>{x['height']}</td>"
        f"<td class='mono'>{esc(x['txid'])}</td><td class='n'>{xmrf(x['amount'], 12)}</td></tr>" for x in other)
    body = (f"<h1>Zuflüsse {year_select('/zufluesse', year)}</h1>"
            f"<table><tr><th>Zeitpunkt</th><th class='n'>Block</th><th>TXID</th><th class='n'>XMR</th>"
            f"<th class='n'>Kurs EUR</th><th class='n'>Wert EUR</th><th>Kursquelle</th></tr>"
            f"{tr or '<tr><td colspan=7 class=mut>Keine Zuflüsse</td></tr>'}</table>"
            f"<h2>Sonstige Zugänge (kein Mining, nicht als Einnahme gezählt)</h2>"
            f"<p class='mut'>Die Nur-Lesen-Wallet sieht auch Rückgeld eigener Überweisungen. Solche Eingänge stehen hier.</p>"
            f"<table><tr><th>Zeitpunkt</th><th class='n'>Block</th><th>TXID</th><th class='n'>XMR</th></tr>"
            f"{tr2 or '<tr><td colspan=4 class=mut>keine</td></tr>'}</table>")
    return page("/zufluesse", "Zuflüsse", body)


def p_power(q) -> str:
    year = int(q.get("jahr", [datetime.now(CFG.tz).year])[0])
    pm = ledger.power_by_month(CFG, year)
    tr = "".join(
        f"<tr><td>{p['month']}</td><td>{esc(p['device'])}</td><td class='n'>{de((p['secs'] or 0) / 3600, 1)} h</td>"
        f"<td class='n'>{de(p['hashrate'], 0)} H/s</td><td class='n'>{de(p['watts_eff'], 1)} W</td>"
        f"<td class='n'>{de(p['kwh'], 3)}</td><td class='n'>{de(p['tariff_eff'], 2)} ct</td>"
        f"<td class='n'>{eurf(p['cost'])}</td></tr>" for p in pm)
    tot = ledger.power_by_device(CFG, year)
    tr2 = "".join(f"<tr><td>{esc(p['device'])}</td><td class='n'>{de((p['secs'] or 0) / 3600, 1)} h</td>"
                  f"<td class='n'>{de(p['kwh'], 3)}</td><td class='n'>{eurf(p['cost'])}</td></tr>" for p in tot)
    sum_style = "style='font-weight:600;background:#f0f2f5'"
    if tot:
        tr2 += (f"<tr {sum_style}><td>Summe</td><td class='n'>{de(sum(p['secs'] or 0 for p in tot) / 3600, 1)} h</td>"
                f"<td class='n'>{de(sum(p['kwh'] or 0 for p in tot), 3)}</td>"
                f"<td class='n'>{eurf(sum(p['cost'] or 0 for p in tot))}</td></tr>")
    months: dict[str, dict] = {}
    for p in pm:
        mo = months.setdefault(p["month"], {"secs": 0, "kwh": 0.0, "cost": 0.0})
        mo["secs"] += p["secs"] or 0
        mo["kwh"] += p["kwh"] or 0.0
        mo["cost"] += p["cost"] or 0.0
    tr3 = "".join(
        f"<tr><td>{mo}</td><td class='n'>{de(v['secs'] / 3600, 1)} h</td><td class='n'>{de(v['kwh'], 3)}</td>"
        f"<td class='n'>{de(v['cost'] / v['kwh'] * 100 if v['kwh'] else None, 2)} ct</td>"
        f"<td class='n'>{eurf(v['cost'])}</td></tr>" for mo, v in months.items())
    tariffs = ", ".join(f"ab {t.valid_from.strftime('%d.%m.%Y')}: {de(t.ct_per_kwh)} ct/kWh" for t in CFG.tariffs)
    body = (f"<h1>Strom {year_select('/strom', year)}</h1>"
            f"<p class='mut'>Methode: gemessener Mehrverbrauch × protokollierte Mining-Zeit × Strompreis "
            f"({esc(tariffs)}). Abfrage alle {CFG.poll_seconds} s.</p>"
            f"<h2>Je Gerät</h2><table><tr><th>Gerät</th><th class='n'>Mining-Zeit</th><th class='n'>kWh</th>"
            f"<th class='n'>Kosten</th></tr>{tr2 or '<tr><td colspan=4 class=mut>noch keine Daten</td></tr>'}</table>"
            f"<h2>Je Monat, alle Geräte</h2><table><tr><th>Monat</th><th class='n'>Mining-Zeit (Geräte-h)</th>"
            f"<th class='n'>kWh</th><th class='n'>Ø Preis</th><th class='n'>Kosten</th></tr>"
            f"{tr3 or '<tr><td colspan=5 class=mut>noch keine Daten</td></tr>'}</table>"
            f"<h2>Je Monat und Gerät</h2><table><tr><th>Monat</th><th>Gerät</th><th class='n'>Mining-Zeit</th>"
            f"<th class='n'>Ø Hashrate</th><th class='n'>Ø Watt</th><th class='n'>kWh</th><th class='n'>Ø Preis</th>"
            f"<th class='n'>Kosten</th></tr>{tr or '<tr><td colspan=8 class=mut>noch keine Daten</td></tr>'}</table>")
    return page("/strom", "Strom", body)


# ---------- Auswertung ----------
STATE_COLOR = {"mint": "var(--ok)", "pausiert": "#f5b971", "nicht erreichbar": "#d0d5dd"}


def analysis_range(q) -> tuple[datetime, datetime, str]:
    """Zeitraum aus ?zeitraum=<preset> oder ?von=…&bis=… (datetime-local, lokale Zeit)."""
    von, bis = (q.get("von") or [""])[0], (q.get("bis") or [""])[0]
    if von and bis:
        start = datetime.fromisoformat(von).replace(tzinfo=CFG.tz)
        end = datetime.fromisoformat(bis).replace(tzinfo=CFG.tz)
        if end <= start:
            raise ValueError("Ende muss nach dem Beginn liegen")
        return start, end, ""
    key = (q.get("zeitraum") or ["24h"])[0]
    if key not in dict(activity.PRESETS):
        raise ValueError("unbekannter Zeitraum")
    start, end = activity.preset_range(CFG, key)
    return start, end, key


def _hm(secs) -> str:
    return f"{de((secs or 0) / 3600, 2)} h"


def _pct(part, whole) -> str:
    return f"<span class='mut'>({de(100 * part / whole, 0)} %)</span>" if whole else ""


def _xmr(v, digits=8) -> str:
    return "–" if v is None else f"{de(v, digits)} XMR"


def p_analysis(q) -> str:
    try:
        start, end, key = analysis_range(q)
    except ValueError as e:
        return page("/auswertung", "Auswertung", f"<h1>Auswertung</h1><p class='note'>Ungültiger Zeitraum: {esc(e)}</p>")
    a = activity.analyse(CFG, start, end)
    s_, e_ = a["start"], a["end"]
    span = (e_ - s_).total_seconds()
    t = a["total"]
    fmt = "%Y-%m-%dT%H:%M"

    presets = " ".join(
        f'<a class="btn" style="{"" if k == key else "background:#eef0f3;color:var(--ink)"}" '
        f'href="/auswertung?zeitraum={k}">{esc(lbl)}</a>' for k, lbl in activity.PRESETS)
    form = (f'<form class="inline" method="get" action="/auswertung">'
            f'<label>von<input type="datetime-local" name="von" value="{s_.strftime(fmt)}"></label>'
            f'<label>bis<input type="datetime-local" name="bis" value="{e_.strftime(fmt)}"></label>'
            f'<button>Auswerten</button>'
            f'<a class="btn" style="background:#475467" href="/auswertung.csv?von={s_.strftime(fmt)}&bis={e_.strftime(fmt)}">CSV</a></form>')

    luck = "" if a["luck"] is None else f" · {de(a['luck'] * 100, 0)} % des Erwartungswerts"
    result = None if a["exp_eur"] is None else ledger.eur(a["exp_eur"]) - ledger.eur(Decimal(str(t["cost"])))
    cards = f"""<div class="grid">
      <div class="card"><div class="k">Mining-Zeit (alle Rechner)</div><div class="v">{_hm(t['mining_s'])}</div>
        <div class="s">pausiert {_hm(t['paused_s'])} · nicht erreichbar {_hm(t['offline_s'])}</div></div>
      <div class="card"><div class="k">Hashes</div><div class="v">{de(t['hashes'] / 1e6, 1)} Mio.</div>
        <div class="s">zusammen Ø {de(t['hr_eff'], 0)} H/s über den ganzen Zeitraum</div></div>
      <div class="card"><div class="k">Strom (inkl. NAS)</div><div class="v">{eurf(t['cost'])}</div>
        <div class="s">{de(t['kwh'], 3)} kWh</div></div>
      <div class="card"><div class="k">Rechnerischer Gegenwert</div><div class="v">{_xmr(t['exp_xmr'])}</div>
        <div class="s">≈ {eurf(None if a['exp_eur'] is None else ledger.eur(a['exp_eur']))} (Ø Kurs {eurf(a['price'])})</div></div>
      <div class="card"><div class="k">Ausgezahlt im Zeitraum</div><div class="v">{_xmr(a['paid_xmr'])}</div>
        <div class="s">{len(a['payouts'])} {"Auszahlung" if len(a['payouts']) == 1 else "Auszahlungen"} · {eurf(ledger.eur(a['paid_eur']))}{luck}</div></div>
      <div class="card"><div class="k">Gegenwert − Strom</div><div class="v">{eurf(result)}</div>
        <div class="s">rechnerisch, ohne Glück/Pech bei Auszahlungen</div></div>
    </div>"""

    rows = ""
    for dev, d in a["devices"].items():
        polled = d["mining_s"] + d["paused_s"] + d["offline_s"]
        if dev == activity.NAS_DEVICE:
            rows += (f"<tr><td>{esc(dev)}</td><td colspan=6 class='mut'>Pauschale für Node + Pool</td>"
                     f"<td class='n'>{de(d['kwh'], 3)}</td><td class='n'>{eurf(d['cost'])}</td><td></td></tr>")
            continue
        rows += (f"<tr><td>{esc(dev)}</td><td class='n'>{_hm(d['mining_s'])} {_pct(d['mining_s'], polled)}</td>"
                 f"<td class='n'>{_hm(d['paused_s'])}</td><td class='n'>{_hm(d['offline_s'])}</td>"
                 f"<td class='n'>{de(d['hr_avg'], 0)}</td><td class='n'>{de(d['hr_max'], 0)}</td>"
                 f"<td class='n'>{de(d['hashes'] / 1e6, 1)}</td><td class='n'>{de(d['kwh'], 3)}</td>"
                 f"<td class='n'>{eurf(d['cost'])}</td><td class='n'>{de(d['exp_xmr'], 8)}</td></tr>")
    sum_style = "style='font-weight:600;background:#f0f2f5'"
    polled = t["mining_s"] + t["paused_s"] + t["offline_s"]
    if a["devices"]:
        rows += (f"<tr {sum_style}><td>Gesamt</td><td class='n'>{_hm(t['mining_s'])} {_pct(t['mining_s'], polled)}</td>"
                 f"<td class='n'>{_hm(t['paused_s'])}</td><td class='n'>{_hm(t['offline_s'])}</td>"
                 f"<td class='n' title='zusammen, über den ganzen Zeitraum'>{de(t['hr_eff'], 0)}*</td><td class='n'>–</td>"
                 f"<td class='n'>{de(t['hashes'] / 1e6, 1)}</td><td class='n'>{de(t['kwh'], 3)}</td>"
                 f"<td class='n'>{eurf(t['cost'])}</td><td class='n'>{de(t['exp_xmr'], 8)}</td></tr>")
    table = (f"<h2>Je Gerät</h2><div style='overflow-x:auto'><table><tr><th>Gerät</th><th class='n'>mint</th><th class='n'>pausiert</th>"
             f"<th class='n'>nicht erreichbar</th><th class='n'>Ø H/s</th><th class='n'>max H/s</th>"
             f"<th class='n'>Hashes (Mio.)</th><th class='n'>kWh</th><th class='n'>Kosten</th>"
             f"<th class='n'>erwartet XMR</th></tr>"
             f"{rows or '<tr><td colspan=10 class=mut>Keine Daten im Zeitraum</td></tr>'}</table></div>"
             f"<p class='mut' style='font-size:12.5px'>Ø H/s je Gerät: während es mint. * Gesamt: alle Rechner "
             f"zusammen, gemittelt über den ganzen Zeitraum.</p>")

    timeline = ""
    if a["segments"]:
        legend = " ".join(f"<span class='pill' style='background:{c};color:{'#fff' if st == 'mint' else 'var(--ink)'}'>"
                          f"{st}</span>" for st, c in STATE_COLOR.items())
        timeline = f"<h2>Zeitleiste</h2><p class='mut'>{legend} · weiß = keine Abfrage</p>"
        for dev, segs in sorted(a["segments"].items()):
            if dev == activity.NAS_DEVICE:
                continue
            bars, lst = "", ""
            for st, a0, b0, iv, hs in segs:
                left = max(0.0, (a0 - s_.timestamp()) / span * 100)
                width = max(0.15, (b0 - max(a0, s_.timestamp())) / span * 100)
                when = (f"{datetime.fromtimestamp(a0, CFG.tz).strftime('%d.%m. %H:%M')}–"
                        f"{datetime.fromtimestamp(b0, CFG.tz).strftime('%H:%M')}")
                label = f"{when} {st}"
                bars += (f"<div title='{esc(label)}' style='position:absolute;top:0;bottom:0;left:{left:.3f}%;"
                         f"width:{width:.3f}%;background:{STATE_COLOR[st]}'></div>")
                avg = f"Ø {de(hs / iv, 0)} H/s" if st == "mint" and iv else ""
                lst += (f"<tr><td>{when}</td>"
                        f"<td>{st}</td><td class='n'>{de(iv / 60, 0)} min</td><td class='n'>{avg}</td></tr>")
            timeline += (f"<p style='margin:10px 0 4px'><b>{esc(dev)}</b></p>"
                         f"<div style='position:relative;height:22px;background:#fff;border:1px solid var(--line);"
                         f"border-radius:6px;overflow:hidden'>{bars}</div>"
                         f"<details><summary class='mut' style='font-size:13px;cursor:pointer'>{len(segs)} Abschnitte</summary>"
                         f"<table><tr><th>Zeit</th><th>Status</th><th class='n'>Dauer</th><th class='n'>Hashrate</th></tr>"
                         f"{lst}</table></details>")
        timeline += (f"<p class='mut' style='font-size:12.5px'>{s_.strftime('%d.%m. %H:%M')} bis "
                     f"{e_.strftime('%d.%m. %H:%M')}</p>")

    days_html = ""
    if span > 36 * 3600 and a["days"]:
        per_day: dict[str, dict] = {}
        for (day, dev), d in a["days"].items():
            x = per_day.setdefault(day, {"mining_s": 0, "hashes": 0.0, "kwh": 0.0, "cost": 0.0, "exp": Decimal(0)})
            if dev != activity.NAS_DEVICE:
                x["mining_s"] += d["mining_s"]
                x["hashes"] += d["hashes"]
                x["exp"] += d["exp_xmr"]
            x["kwh"] += d["kwh"]
            x["cost"] += d["cost"]
        def day_span(day: str) -> float:
            d0 = datetime.fromisoformat(day).replace(tzinfo=CFG.tz)
            d1 = d0 + timedelta(days=1)
            return max((min(d1, e_) - max(d0, s_)).total_seconds(), 1.0)
        tr = "".join(
            f"<tr><td>{datetime.fromisoformat(day).strftime('%d.%m.%Y')}</td><td class='n'>{_hm(x['mining_s'])}</td>"
            f"<td class='n'>{de(x['hashes'] / day_span(day), 0)}</td>"
            f"<td class='n'>{de(x['hashes'] / 1e6, 1)}</td><td class='n'>{de(x['kwh'], 3)}</td>"
            f"<td class='n'>{eurf(x['cost'])}</td><td class='n'>{de(x['exp'], 8)}</td></tr>"
            for day, x in per_day.items())
        days_html = (f"<h2>Je Tag, alle Geräte</h2><div style='overflow-x:auto'><table><tr><th>Tag</th>"
                     f"<th class='n'>Mining-Zeit</th><th class='n'>Ø H/s zusammen</th><th class='n'>Hashes (Mio.)</th><th class='n'>kWh</th>"
                     f"<th class='n'>Kosten</th><th class='n'>erwartet XMR</th></tr>{tr}</table></div>")

    pay = "".join(
        f"<tr><td>{datetime.fromtimestamp(p['ts'], CFG.tz).strftime('%d.%m.%Y %H:%M')}</td><td class='n'>{p['height']}</td>"
        f"<td class='n'>{xmrf(p['amount'], 8)}</td><td class='n'>{eurf(None if not p['price_eur'] else Decimal(p['price_eur']))}</td></tr>"
        for p in a["payouts"])
    payouts = (f"<h2>Auszahlungen im Zeitraum</h2><table><tr><th>Zeit</th><th class='n'>Block</th>"
               f"<th class='n'>XMR</th><th class='n'>Kurs</th></tr>"
               f"{pay or '<tr><td colspan=4 class=mut>keine</td></tr>'}</table>")

    nerr = db.get_meta("network_error") or ""
    net_note = (f'<span class="pill bad">Node-Fehler</span> <span class="mut">{esc(nerr)}</span> ' if nerr else "")
    missing = (f"<p class='note'>Für {_hm(t['exp_missing_s'])} Mining-Zeit fehlen Difficulty-Werte vom Node; "
               f"dieser Anteil fehlt im Gegenwert.</p>") if t["exp_missing_s"] else ""
    net = (f"<h2>Netz und Methode</h2>{missing}<p>{net_note}Ø Difficulty "
           f"{de(a['difficulty'] / 1e9, 1) + ' G' if a['difficulty'] else '–'}, Ø Blockbelohnung "
           f"{_xmr(a['reward'], 4) if a['reward'] else '–'} ({a['net_count']} Werte vom eigenen Node). "
           f"Datenbasis: {a['resolution']}{' (auf volle Stunden gerundet)' if not a['minute'] else ''}.</p>"
           f"<p class='mut'>Hashes = gemeldete Hashrate × Abfrageintervall (Abfrage alle {CFG.poll_seconds} s). "
           f"Rechnerischer Gegenwert = Hashes ÷ Difficulty × Blockbelohnung, je Stunde mit dem Wert vom eigenen Node; "
           f"P2Pool erhebt keine Gebühr, Uncles/Orphans sind nicht berücksichtigt. Auszahlungen kommen nur, wenn "
           f"P2Pool einen Block findet, während ein eigener Share im PPLNS-Fenster liegt – über kurze Zeiträume "
           f"weichen sie deshalb stark vom Gegenwert ab. Reine Auswertung; Grundlage für Bericht und Steuer bleiben "
           f"die Seiten Zuflüsse und Strom.</p>")

    body = (f"<h1>Auswertung</h1><p>{presets}</p>{form}"
            f"<p class='mut'>{s_.strftime('%d.%m.%Y %H:%M')} bis {e_.strftime('%d.%m.%Y %H:%M')}</p>"
            f"{cards}{table}{timeline}{days_html}{payouts}{net}")
    return page("/auswertung", "Auswertung", body)


def analysis_csv(q) -> bytes:
    start, end, _ = analysis_range(q)
    a = activity.analyse(CFG, start, end)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    num = lambda v, n: f"{float(v):.{n}f}".replace(".", ",")  # noqa: E731
    w.writerow(["Tag", "Gerät", "Mining h", "pausiert h", "nicht erreichbar h", "Ø H/s", "max H/s", "Hashes",
                "kWh", "Kosten EUR", "erwartet XMR"])
    for (day, dev), d in a["days"].items():
        w.writerow([day, dev, num(d["mining_s"] / 3600, 3), num(d["paused_s"] / 3600, 3),
                    num(d["offline_s"] / 3600, 3), num(d["hr_avg"], 0), num(d["hr_max"], 0), num(d["hashes"], 0),
                    num(d["kwh"], 4), num(d["cost"], 4), num(d["exp_xmr"], 12)])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def p_lots(q) -> str:
    h = ledger.holdings(CFG)
    today = datetime.now(CFG.tz).date()
    tr = ""
    for l in h["lots"]:
        free = today >= l.free_from
        st = ('<span class="pill ok">steuerfrei</span>' if free else
              f'<span class="pill warn">noch {(l.free_from - today).days} Tage</span>')
        if l.remaining == 0:
            st = '<span class="pill mut">abgegangen</span>'
        tr += (f"<tr><td>{dfmt(l.day)}</td><td class='n'>{xmrf(l.amount, 8)}</td>"
               f"<td class='n'>{eurf(None if l.cost_total is None else ledger.eur(l.cost_total))}</td>"
               f"<td>{dfmt(l.free_from)}</td><td class='n'>{xmrf(l.remaining, 8)}</td><td>{st}</td>"
               f"<td class='mono mut'>{esc(l.txid[:16])}…</td></tr>")
    body = (f"<h1>Lose (FIFO)</h1><p class='mut'>Jede Mining-Auszahlung ist ein eigenes Los mit Anschaffungsdatum "
            f"und Anschaffungskosten (Wert beim Zufluss). „steuerfrei ab“ = erster Tag nach Ablauf der Jahresfrist.</p>"
            f"<table><tr><th>Zufluss</th><th class='n'>XMR</th><th class='n'>AK</th><th>steuerfrei ab</th>"
            f"<th class='n'>Rest</th><th>Status</th><th>TXID</th></tr>"
            f"{tr or '<tr><td colspan=7 class=mut>Noch keine Lose</td></tr>'}</table>")
    return page("/lose", "Lose", body)


def p_disposals(q, msg: str = "") -> str:
    _, disposals = ledger.load_lots_and_disposals(CFG)
    tr = ""
    for d in reversed(disposals):
        tg = d.taxable_gain
        tr += (f"<tr><td>{dfmt(d.day)}</td><td>{esc(d.kind_label)}</td><td class='n'>{xmrf(d.amount, 8)}</td>"
               f"<td class='n'>{eurf(d.proceeds)}</td>"
               f"<td class='n'>{'–' if d.kind == 'own' else eurf(None if tg is None else ledger.eur(tg))}</td>"
               f"<td class='mut'>{esc(d.txid[:16])} {esc(d.note)}"
               f"{' <span class=bad>Bestand reicht nicht</span>' if d.shortfall else ''}</td>"
               f"<td><form method='post' action='/abgaenge/loeschen' onsubmit=\"return confirm('Abgang löschen?')\">"
               f"<input type='hidden' name='id' value='{d.id}'><button class='sec'>Löschen</button></form></td></tr>")
    today = datetime.now(CFG.tz).date().isoformat()
    form = f"""
    <form class="inline" method="post" action="/abgaenge">
      <label>Datum<input type="date" name="datum" value="{today}" required></label>
      <label>Uhrzeit<input type="time" name="uhrzeit" value="12:00"></label>
      <label>Menge XMR (inkl. Gebühr)<input name="menge" placeholder="0,05" required></label>
      <label>Art<select name="art"><option value="sale">Verkauf/Tausch</option><option value="spend">Bezahlung</option>
        <option value="own">Übertrag auf eigene Wallet</option></select></label>
      <label>Erlös/Gegenwert EUR<input name="erloes" placeholder="bei Verkauf/Bezahlung"></label>
      <label>TXID<input name="txid" style="min-width:220px"></label>
      <label>Notiz<input name="notiz"></label>
      <button>Abgang erfassen</button>
    </form>"""
    body = (f"<h1>Abgänge</h1>{f'<p class=note>{esc(msg)}</p>' if msg else ''}"
            f"<p class='mut'>Die Nur-Lesen-Wallet kann Ausgänge nicht erkennen. Trage jede Überweisung aus der "
            f"Mining-Wallet hier ein: Menge = an andere gesendeter Betrag + Netzwerkgebühr (das Rückgeld an "
            f"dich selbst nicht mitzählen). Bei Tausch in eine andere Kryptowährung ist der Erlös der EUR-Wert "
            f"des Erhaltenen. Verbrauch nach FIFO.</p>{form}"
            f"<h2>Erfasste Abgänge</h2><table><tr><th>Datum</th><th>Art</th><th class='n'>XMR</th>"
            f"<th class='n'>Erlös</th><th class='n'>stpfl. Gewinn</th><th>TXID / Notiz</th><th></th></tr>"
            f"{tr or '<tr><td colspan=7 class=mut>keine</td></tr>'}</table>")
    return page("/abgaenge", "Abgänge", body)


def p_calc(q) -> str:
    cur = prices.current_price(CFG)
    menge = q.get("menge", [""])[0]
    datum = q.get("datum", [datetime.now(CFG.tz).date().isoformat()])[0]
    kurs = q.get("kurs", [de(cur, 2) if cur else ""])[0]
    form = f"""
    <form class="inline" method="get" action="/rechner">
      <label>Menge XMR<input name="menge" value="{esc(menge)}" placeholder="z. B. 0,1" required></label>
      <label>Verkaufsdatum<input type="date" name="datum" value="{esc(datum)}"></label>
      <label>Kurs EUR/XMR<input name="kurs" value="{esc(kurs)}"></label>
      <button>Berechnen</button>
    </form>"""
    result = ""
    if menge:
        try:
            amt, k, d = parse_dec(menge), parse_dec(kurs), date.fromisoformat(datum)
            r = ledger.sale_calc(CFG, amt, d, k)
            pill_tax = '<span class="pill warn">steuerpflichtig</span>'
            pill_free = '<span class="pill ok">steuerfrei</span>'
            tr = "".join(
                f"<tr><td>{dfmt(x['lot'].day)}</td><td class='n'>{xmrf(x['amount'], 8)}</td>"
                f"<td class='n'>{eurf(None if x['cost'] is None else ledger.eur(x['cost']))}</td>"
                f"<td class='n'>{eurf(ledger.eur(x['proceeds']))}</td>"
                f"<td class='n'>{eurf(None if x['gain'] is None else ledger.eur(x['gain']))}</td>"
                f"<td>{dfmt(x['lot'].free_from)}</td>"
                f"<td>{pill_tax if x['taxable'] else pill_free}</td></tr>"
                for x in r["rows"])
            short = (f'<p class="note">Bestand reicht nicht: es fehlen {xmrf(r["shortfall"], 8)} XMR.</p>'
                     if r["shortfall"] else "")
            latest_free = max((x["lot"].free_from for x in r["rows"] if x["taxable"]), default=None)
            hint = (f"<p>Bei einem Verkauf ab dem <b>{dfmt(latest_free)}</b> wären alle betroffenen Lose "
                    f"außerhalb der Jahresfrist (bei gleichem Bestand).</p>") if latest_free else ""
            result = (f"{short}<div class='grid' style='margin-top:14px'>"
                      f"<div class='card'><div class='k'>steuerpflichtiger Gewinn (§ 23)</div>"
                      f"<div class='v'>{eurf(None if r['taxable_gain'] is None else ledger.eur(r['taxable_gain']))}</div>"
                      f"<div class='s'>{xmrf(r['taxable_amount'], 8)} XMR innerhalb der Jahresfrist</div></div>"
                      f"<div class='card'><div class='k'>steuerfreier Gewinn</div>"
                      f"<div class='v'>{eurf(None if r['free_gain'] is None else ledger.eur(r['free_gain']))}</div>"
                      f"<div class='s'>{xmrf(r['free_amount'], 8)} XMR außerhalb der Jahresfrist</div></div></div>"
                      f"{hint}<h2>Betroffene Lose (FIFO)</h2><table><tr><th>Los vom</th><th class='n'>XMR</th>"
                      f"<th class='n'>AK</th><th class='n'>Erlös</th><th class='n'>Gewinn</th><th>steuerfrei ab</th>"
                      f"<th></th></tr>{tr}</table>"
                      f"<p class='mut'>Freigrenze § 23 Abs. 3 S. 5 EStG: Gewinne aller privaten Veräußerungsgeschäfte "
                      f"im Kalenderjahr unter 1.000 € bleiben steuerfrei. Gebühren sind hier nicht abgezogen.</p>")
        except (InvalidOperation, ValueError) as e:
            result = f"<p class='note'>Eingabe prüfen: {esc(e)}</p>"
    body = (f"<h1>Verkaufs-Rechner (§ 23 EStG)</h1><p class='mut'>Simuliert einen Verkauf oder Tausch aus dem "
            f"aktuellen Bestand nach FIFO – es wird nichts gespeichert.</p>{form}{result}")
    return page("/rechner", "Verkaufs-Rechner", body)


# ---------- HTTP ----------
class Handler(BaseHTTPRequestHandler):
    server_version = "xmr-ledger"

    def log_message(self, fmt, *args):
        log.debug(fmt, *args)

    def _auth(self) -> bool:
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic "):
            try:
                user, _, pw = base64.b64decode(h[6:]).decode().partition(":")
                if hmac.compare_digest(user, CFG.web_user) and hmac.compare_digest(pw, CFG.web_password):
                    return True
            except Exception:  # noqa: BLE001
                pass
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="XMR-Ledger"')
        self.end_headers()
        return False

    def _send(self, body: bytes, ctype="text/html; charset=utf-8", status=200, filename=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, to: str):
        self.send_response(303)
        self.send_header("Location", to)
        self.end_headers()

    def _same_origin(self) -> bool:
        """Schutz gegen CSRF: POST nur von Seiten dieses Dashboards annehmen."""
        host = self.headers.get("Host", "")
        src = self.headers.get("Origin") or self.headers.get("Referer") or ""
        if not src:
            return False
        if src == "null":
            return False
        return urllib.parse.urlparse(src).netloc == host

    def handle_one_request(self):
        try:
            super().handle_one_request()
        finally:
            db.close_thread()

    def do_GET(self):  # noqa: N802
        u = urllib.parse.urlparse(self.path)
        if u.path == "/health":  # ohne Passwort, für den Docker-Healthcheck
            self._send(b"ok", "text/plain; charset=utf-8")
            return
        if not self._auth():
            return
        q = urllib.parse.parse_qs(u.query)
        try:
            try:
                year = int(q.get("jahr", [datetime.now(CFG.tz).year])[0])
                if not 2000 <= year <= 2200:
                    raise ValueError
            except ValueError:
                self._send("Ungültiges Jahr".encode(), "text/plain; charset=utf-8", 400)
                return
            if u.path == "/":
                self._send(p_overview(q).encode())
            elif u.path == "/api/live":
                self._send(json.dumps(overview_live(year), ensure_ascii=False).encode(),
                           "application/json; charset=utf-8")
            elif u.path == "/zufluesse":
                self._send(p_inflows(q).encode())
            elif u.path == "/strom":
                self._send(p_power(q).encode())
            elif u.path == "/auswertung":
                self._send(p_analysis(q).encode())
            elif u.path == "/auswertung.csv":
                try:
                    data = analysis_csv(q)
                except ValueError as e:
                    self._send(f"Ungültiger Zeitraum: {e}".encode(), "text/plain; charset=utf-8", 400)
                    return
                self._send(data, "text/csv; charset=utf-8", filename="moneta-auswertung.csv")
            elif u.path == "/lose":
                self._send(p_lots(q).encode())
            elif u.path == "/abgaenge":
                self._send(p_disposals(q).encode())
            elif u.path == "/rechner":
                self._send(p_calc(q).encode())
            elif u.path == "/bericht.xlsx":
                self._send(report.build_xlsx(CFG, year),
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           filename=f"monero-mining-{year}.xlsx")
            elif u.path == "/zufluesse.csv":
                self._send(report.build_csv(CFG, year), "text/csv; charset=utf-8",
                           filename=f"monero-zufluesse-{year}.csv")
            else:
                self._send(b"Nicht gefunden", "text/plain; charset=utf-8", 404)
        except Exception as e:  # noqa: BLE001
            log.exception("Fehler bei %s", self.path)
            self._send(f"Fehler: {e}".encode(), "text/plain; charset=utf-8", 500)

    def do_POST(self):  # noqa: N802
        if not self._auth():
            return
        if not self._same_origin():
            self._send("Abgelehnt: Anfrage kam nicht vom Dashboard".encode(), "text/plain; charset=utf-8", 403)
            return
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        form = {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(n).decode()).items()}
        try:
            if u.path == "/abgaenge":
                d = date.fromisoformat(form["datum"])
                t = dtime.fromisoformat(form.get("uhrzeit") or "12:00")
                ts = int(datetime.combine(d, t, tzinfo=CFG.tz).timestamp())
                amount = int((parse_dec(form["menge"]) * ledger.PICO).to_integral_value())
                if amount <= 0:
                    raise ValueError("Menge muss größer als 0 sein")
                kind = form.get("art", "sale")
                if kind not in ("sale", "spend", "own"):
                    raise ValueError("ungültige Art")
                proceeds = None
                if kind != "own":
                    if not form.get("erloes"):
                        raise ValueError("Bei Verkauf/Tausch/Bezahlung bitte den Erlös in EUR angeben")
                    proceeds = str(parse_dec(form["erloes"]))
                with db.write_lock:
                    c = db.get()
                    c.execute("INSERT INTO disposals(ts, amount, kind, proceeds_eur, txid, note, created) "
                              "VALUES(?,?,?,?,?,?,?)",
                              (ts, amount, kind, proceeds, form.get("txid", "").strip(),
                               form.get("notiz", "").strip(), db.now()))
                    c.commit()
                self._redirect("/abgaenge")
            elif u.path == "/abgaenge/loeschen":
                with db.write_lock:
                    c = db.get()
                    c.execute("DELETE FROM disposals WHERE id=?", (int(form["id"]),))
                    c.commit()
                self._redirect("/abgaenge")
            else:
                self._send(b"Nicht gefunden", "text/plain; charset=utf-8", 404)
        except (KeyError, ValueError, InvalidOperation) as e:
            self._send(p_disposals({}, msg=f"Nicht gespeichert: {e}").encode(), status=400)


def serve(cfg: Config, stop) -> ThreadingHTTPServer:
    global CFG
    CFG = cfg
    srv = ThreadingHTTPServer(("0.0.0.0", cfg.web_port), Handler)
    log.info("Dashboard auf Port %s", cfg.web_port)
    return srv
