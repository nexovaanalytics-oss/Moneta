# SPDX-License-Identifier: EUPL-1.2
"""Jahresbericht als Excel-Datei (und Zuflüsse als CSV)."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import devices
import ledger
import version
from config import Config

BOLD = Font(bold=True)
HEAD_FILL = PatternFill("solid", fgColor="DDE6F0")
EUR_FMT = '#,##0.00 "€"'
XMR_FMT = "0.000000000000"
KURS_FMT = '#,##0.0000 "€"'
DATE_FMT = "DD.MM.YYYY"
DT_FMT = "DD.MM.YYYY HH:MM"


def _f(v: Decimal | None):
    return None if v is None else float(v)


def _header(ws, cols: list[tuple[str, int]]):
    for i, (title, width) in enumerate(cols, 1):
        c = ws.cell(row=1, column=i, value=title)
        c.font = BOLD
        c.fill = HEAD_FILL
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = "A2"


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None)


def build_xlsx(cfg: Config, year: int) -> bytes:
    s = ledger.year_summary(cfg, year)
    lots, disposals = ledger.load_lots_and_disposals(cfg)
    wb = Workbook()

    # --- Übersicht ---
    ws = wb.active
    ws.title = "Übersicht"
    ws.column_dimensions["A"].width = 58
    ws.column_dimensions["B"].width = 22
    rows = [
        (f"Monero-Mining – Jahresübersicht {year}", None, None),
        (f"Erstellt am {datetime.now(cfg.tz).strftime('%d.%m.%Y %H:%M')} mit {version.label()}", None, None),
        (f"Mining-Adresse: {cfg.address}", None, None),
        ("", None, None),
        ("Einnahmen aus Mining (Zuflüsse)", None, "h"),
        ("Anzahl Auszahlungen (Coinbase/P2Pool)", s["inflow_count"], None),
        ("Menge XMR", float(ledger.xmr(s["inflow_amount"])), XMR_FMT),
        ("Wert zum Zuflusszeitpunkt (EUR)", _f(s["income"]), EUR_FMT),
        ("davon Zuflüsse ohne Kurs (bitte nachtragen)", s["missing_prices"], None),
        ("", None, None),
        ("Stromkosten (Mehrverbrauch während Mining)", None, "h"),
        ("Strom (kWh)", round(s["power_kwh"], 3), "0.000"),
        ("Stromkosten (EUR)", _f(s["power_cost"]), EUR_FMT),
        ("", None, None),
        ("Ergebnis Einnahmen ./. Stromkosten (EUR)", _f(s["result"]), EUR_FMT),
        ("Unter Freigrenze § 22 Nr. 3 S. 2 EStG (< 256 €)?",
         "ja" if s["under_freigrenze_22"] else "nein", None),
        ("", None, None),
        ("Veräußerungen (§ 23 EStG, FIFO)", None, "h"),
        ("Steuerpflichtiger Gewinn innerhalb Jahresfrist (EUR)", _f(s["gain_23"]), EUR_FMT),
        ("Alle Erlöse/Kurse vorhanden?", "ja" if s["gain_23_complete"] else "nein", None),
        ("Unter Freigrenze § 23 Abs. 3 S. 5 EStG (< 1.000 €)?",
         "ja" if s["under_freigrenze_23"] else "nein", None),
    ]
    for i, (label, val, fmt) in enumerate(rows, 1):
        a = ws.cell(row=i, column=1, value=label)
        if i == 1 or fmt == "h":
            a.font = Font(bold=True, size=13 if i == 1 else 11)
            continue
        if val is not None:
            b = ws.cell(row=i, column=2, value=val)
            if fmt:
                b.number_format = fmt

    r = len(rows) + 2
    notes = [
        "Methodik",
        "Zuflüsse: Coinbase-Eingänge der Mining-Adresse (P2Pool-Auszahlungen), ausgelesen über eine "
        "Nur-Lesen-Wallet am eigenen Monero-Node. Zeitpunkt = Blockzeit.",
        "Kurs: XMR/EUR zum Zuflusszeitpunkt (CoinGecko-5-Minuten-Kurs, nächstgelegener Datenpunkt, max. 15 Min. "
        "Abstand; ersatzweise Tageskurs 00:00 UTC; ggf. manuell). Quelle je Zufluss im Blatt „Zuflüsse“.",
        "Strom: Mehrverbrauch je Gerät (gemessen, siehe Blatt „Geräte“) x automatisch protokollierte "
        "Mining-Laufzeit (XMRig-API, Abfrage alle %d s) x Strompreis." % cfg.poll_seconds,
        "Lose: Jeder Zufluss ist ein Anschaffungsvorgang (AK = Wert beim Zufluss); Verbrauchsfolge FIFO; "
        "steuerfrei ab = Tag nach Ablauf der Jahresfrist.",
        "Hinweis: Freigrenzen gelten jeweils für alle Einkünfte der Einkunftsart; Einordnung (§ 15 / § 22 Nr. 3 EStG) "
        "und Einkünfteerzielungsabsicht sind im Einzelfall zu prüfen.",
    ]
    ws.cell(row=r, column=1, value=notes[0]).font = BOLD
    for j, n in enumerate(notes[1:], 1):
        c = ws.cell(row=r + j, column=1, value=n)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r + j, start_column=1, end_row=r + j, end_column=4)
        ws.row_dimensions[r + j].height = 45

    # --- Zuflüsse ---
    ws = wb.create_sheet("Zuflüsse")
    _header(ws, [("Datum/Uhrzeit", 18), ("Block", 10), ("TXID", 66), ("XMR", 18),
                 ("Kurs EUR/XMR", 15), ("Wert EUR", 13), ("Kursquelle", 42)])
    for i, x in enumerate(s["inflows"], 2):
        ws.cell(row=i, column=1, value=_naive(x["dt"])).number_format = DT_FMT
        ws.cell(row=i, column=2, value=x["height"])
        ws.cell(row=i, column=3, value=x["txid"])
        ws.cell(row=i, column=4, value=float(ledger.xmr(x["amount"]))).number_format = XMR_FMT
        ws.cell(row=i, column=5, value=_f(x["price"])).number_format = KURS_FMT
        ws.cell(row=i, column=6, value=_f(None if x["value"] is None else ledger.eur(x["value"]))).number_format = EUR_FMT
        ws.cell(row=i, column=7, value=x["source"] or "KURS FEHLT")
    n = len(s["inflows"]) + 2
    ws.cell(row=n, column=1, value="Summe").font = BOLD
    if s["inflows"]:
        ws.cell(row=n, column=4, value=f"=SUM(D2:D{n - 1})").number_format = XMR_FMT
        ws.cell(row=n, column=6, value=f"=SUM(F2:F{n - 1})").number_format = EUR_FMT

    # --- Strom ---
    ws = wb.create_sheet("Strom")
    _header(ws, [("Monat", 10), ("Gerät", 28), ("Mining-Stunden", 15), ("Ø Hashrate H/s", 15),
                 ("Ø Watt", 10), ("kWh", 10), ("Ø ct/kWh", 11), ("Kosten EUR", 13)])
    pm = ledger.power_by_month(cfg, year)
    for i, p in enumerate(pm, 2):
        ws.cell(row=i, column=1, value=p["month"])
        ws.cell(row=i, column=2, value=p["device"])
        ws.cell(row=i, column=3, value=round((p["secs"] or 0) / 3600, 2))
        ws.cell(row=i, column=4, value=round(p["hashrate"], 0))
        ws.cell(row=i, column=5, value=None if p["watts_eff"] is None else round(p["watts_eff"], 1))
        ws.cell(row=i, column=6, value=round(p["kwh"] or 0, 3))
        ws.cell(row=i, column=7, value=None if p["tariff_eff"] is None else round(p["tariff_eff"], 2))
        ws.cell(row=i, column=8, value=round(p["cost"] or 0, 2)).number_format = EUR_FMT
    n = len(pm) + 2
    ws.cell(row=n, column=1, value="Summe").font = BOLD
    if pm:
        ws.cell(row=n, column=3, value=f"=SUM(C2:C{n - 1})")
        ws.cell(row=n, column=6, value=f"=SUM(F2:F{n - 1})")
        ws.cell(row=n, column=8, value=f"=SUM(H2:H{n - 1})").number_format = EUR_FMT

    # --- Geräte (Messgrundlage) ---
    ws = wb.create_sheet("Geräte")
    _header(ws, [("Gerät", 28), ("Mehrverbrauch Watt", 18), ("gültig ab", 18), ("Messung / Notiz", 80),
                 ("Quelle", 26)])
    devs = [(m.name, m.watts, "", m.note, "config.toml") for m in cfg.miners]
    if cfg.nas_extra_watts > 0:
        devs.append(("NAS (Node + Pool)", cfg.nas_extra_watts, "", cfg.nas_note, "config.toml"))
    for d in devices.listing():   # im Dashboard gekoppelte Rechner, Watt als Historie
        if d["status"] == "pending":
            continue
        src = "gekoppelt" + (f", stillgelegt {datetime.fromtimestamp(d['retired'], cfg.tz):%d.%m.%Y}"
                             if d["status"] == "retired" and d["retired"] else "")
        for w in d["watts"]:
            devs.append((d["name"], w["watts"], f"{datetime.fromtimestamp(w['valid_from'], cfg.tz):%d.%m.%Y %H:%M}",
                         w["note"], src))
    for i, (name, w, since, note, src) in enumerate(devs, 2):
        ws.cell(row=i, column=1, value=name)
        ws.cell(row=i, column=2, value=w)
        ws.cell(row=i, column=3, value=since)
        ws.cell(row=i, column=4, value=note)
        ws.cell(row=i, column=5, value=src)
    r = len(devs) + 3
    ws.cell(row=r, column=1, value="Strompreise").font = BOLD
    for j, t in enumerate(cfg.tariffs, 1):
        ws.cell(row=r + j, column=1, value=f"ab {t.valid_from.strftime('%d.%m.%Y')}")
        ws.cell(row=r + j, column=2, value=t.ct_per_kwh).number_format = '0.00 "ct/kWh"'

    # --- Lose ---
    ws = wb.create_sheet("Lose (Bestand)")
    _header(ws, [("Zufluss am", 12), ("TXID", 66), ("XMR ursprünglich", 18), ("AK EUR (gesamt)", 15),
                 ("steuerfrei ab", 13), ("XMR Rest in dieser Wallet", 22), ("AK EUR (Rest)", 14),
                 ("XMR übertragen (eigene Wallet)", 24)])
    for i, l in enumerate(lots, 2):
        ws.cell(row=i, column=1, value=l.day).number_format = DATE_FMT
        ws.cell(row=i, column=2, value=l.txid)
        ws.cell(row=i, column=3, value=float(ledger.xmr(l.amount))).number_format = XMR_FMT
        ws.cell(row=i, column=4, value=_f(None if l.cost_total is None else ledger.eur(l.cost_total))).number_format = EUR_FMT
        ws.cell(row=i, column=5, value=l.free_from).number_format = DATE_FMT
        ws.cell(row=i, column=6, value=float(ledger.xmr(l.remaining))).number_format = XMR_FMT
        rest_cost = l.cost_of(l.remaining)
        ws.cell(row=i, column=7, value=_f(None if rest_cost is None else ledger.eur(rest_cost))).number_format = EUR_FMT
        ws.cell(row=i, column=8, value=float(ledger.xmr(l.transferred))).number_format = XMR_FMT

    # --- Veräußerungen ---
    ws = wb.create_sheet("Abgänge")
    _header(ws, [("Datum", 12), ("Art", 22), ("XMR gesamt", 18), ("Erlös EUR gesamt", 15), ("aus Los vom", 12),
                 ("XMR aus Los", 18), ("AK EUR", 12), ("Erlös EUR anteilig", 15), ("Gewinn EUR", 12),
                 ("innerhalb Jahresfrist", 18), ("TXID / Notiz", 50)])
    i = 2
    for d in [d for d in disposals if d.day.year == year]:
        for k, m in enumerate(d.matches or [None]):
            ws.cell(row=i, column=1, value=d.day).number_format = DATE_FMT
            ws.cell(row=i, column=2, value=d.kind_label)
            if k == 0:
                ws.cell(row=i, column=3, value=float(ledger.xmr(d.amount))).number_format = XMR_FMT
                ws.cell(row=i, column=4, value=_f(d.proceeds)).number_format = EUR_FMT
                ws.cell(row=i, column=11, value=" ".join(x for x in (d.txid, d.note) if x))
            if m is not None:
                ws.cell(row=i, column=5, value=m.lot.day).number_format = DATE_FMT
                ws.cell(row=i, column=6, value=float(ledger.xmr(m.amount))).number_format = XMR_FMT
                ws.cell(row=i, column=7, value=_f(None if m.cost is None else ledger.eur(m.cost))).number_format = EUR_FMT
                ws.cell(row=i, column=8, value=_f(None if m.proceeds is None else ledger.eur(m.proceeds))).number_format = EUR_FMT
                ws.cell(row=i, column=9, value=_f(None if m.gain is None else ledger.eur(m.gain))).number_format = EUR_FMT
                ws.cell(row=i, column=10, value="ja" if m.taxable else "nein")
            i += 1
        if d.shortfall:
            ws.cell(row=i, column=2, value="Achtung: Abgang größer als erfasster Mining-Bestand")
            ws.cell(row=i, column=6, value=float(ledger.xmr(d.shortfall))).number_format = XMR_FMT
            i += 1

    # --- Sonstige Zugänge ---
    ws = wb.create_sheet("Sonstige Zugänge")
    _header(ws, [("Datum/Uhrzeit", 18), ("Block", 10), ("TXID", 66), ("XMR", 18), ("Hinweis", 60)])
    for i, x in enumerate(s["other_inflows"], 2):
        ws.cell(row=i, column=1, value=_naive(x["dt"])).number_format = DT_FMT
        ws.cell(row=i, column=2, value=x["height"])
        ws.cell(row=i, column=3, value=x["txid"])
        ws.cell(row=i, column=4, value=float(ledger.xmr(x["amount"]))).number_format = XMR_FMT
        ws.cell(row=i, column=5, value="kein Mining-Zufluss (z. B. Rückgeld eigener Überweisung) – nicht als Einnahme gezählt")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_csv(cfg: Config, year: int) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Datum", "Uhrzeit", "Block", "TXID", "XMR", "Kurs EUR/XMR", "Wert EUR", "Kursquelle"])
    for x in ledger.inflows_in_year(cfg, year):
        w.writerow([
            x["dt"].strftime("%d.%m.%Y"), x["dt"].strftime("%H:%M:%S"), x["height"], x["txid"],
            f"{ledger.xmr(x['amount']):.12f}".replace(".", ","),
            "" if x["price"] is None else f"{x['price']:.4f}".replace(".", ","),
            "" if x["value"] is None else f"{ledger.eur(x['value']):.2f}".replace(".", ","),
            x["source"],
        ])
    return ("﻿" + buf.getvalue()).encode("utf-8")
