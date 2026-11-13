# SPDX-License-Identifier: EUPL-1.2
"""Steuerliche Auswertung: Lose (FIFO), Haltefristen, Jahresübersicht, Verkaufs-Rechner.

Grundlage (Verwaltungsauffassung, BMF-Schreiben vom 06.03.2025):
- Mining-Auszahlungen sind Einnahmen zum Marktkurs im Zeitpunkt des Zugangs
  (je nach Einzelfall § 15 oder § 22 Nr. 3 EStG).
- Die erhaltenen Einheiten gelten als angeschafft; Anschaffungskosten = Wert beim Zufluss;
  Veräußerung innerhalb eines Jahres ist privates Veräußerungsgeschäft (§ 23 Abs. 1 S. 1 Nr. 2 EStG).
- Verbrauchsfolge hier: FIFO.
Die Einordnung im Einzelfall trifft der Steuerpflichtige; das Tool liefert Zahlen und Belege.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

import db
from config import Config

PICO = Decimal(10) ** 12
CENT = Decimal("0.01")
FREIGRENZE_22_3 = Decimal("256")
FREIGRENZE_23 = Decimal("1000")


def xmr(pico: int | Decimal) -> Decimal:
    return Decimal(pico) / PICO


def eur(v: Decimal) -> Decimal:
    return v.quantize(CENT, rounding=ROUND_HALF_UP)


def steuerfrei_ab(acquired: date) -> date:
    """Erster Tag, an dem eine Veräußerung außerhalb der Jahresfrist liegt (§§ 187 Abs. 1, 188 Abs. 2, 3 BGB)."""
    try:
        end = acquired.replace(year=acquired.year + 1)
    except ValueError:  # 29. Februar
        end = date(acquired.year + 1, 2, 28)
    return end + timedelta(days=1)


@dataclass
class Lot:
    txid: str
    ts: int
    day: date
    amount: int                 # Piconero ursprünglich
    price: Decimal | None       # EUR/XMR beim Zufluss
    remaining: int = 0
    transferred: int = 0        # per Eigenübertrag aus dieser Wallet hinaus

    @property
    def cost_total(self) -> Decimal | None:
        return None if self.price is None else xmr(self.amount) * self.price

    def cost_of(self, pico: int) -> Decimal | None:
        return None if self.price is None else xmr(pico) * self.price

    @property
    def free_from(self) -> date:
        return steuerfrei_ab(self.day)


@dataclass
class Match:
    lot: Lot
    amount: int
    cost: Decimal | None
    proceeds: Decimal | None
    taxable: bool

    @property
    def gain(self) -> Decimal | None:
        if self.cost is None or self.proceeds is None:
            return None
        return self.proceeds - self.cost


@dataclass
class Disposal:
    id: int
    ts: int
    day: date
    amount: int
    kind: str
    proceeds: Decimal | None
    txid: str
    note: str
    matches: list[Match] = field(default_factory=list)
    shortfall: int = 0

    @property
    def kind_label(self) -> str:
        return {"sale": "Verkauf/Tausch", "spend": "Bezahlung", "own": "Übertrag eigene Wallet"}.get(self.kind, self.kind)

    @property
    def taxable_gain(self) -> Decimal | None:
        vals = [m.gain for m in self.matches if m.taxable]
        if any(v is None for v in vals):
            return None
        return sum(vals, Decimal(0))

    @property
    def free_gain(self) -> Decimal | None:
        vals = [m.gain for m in self.matches if not m.taxable]
        if any(v is None for v in vals):
            return None
        return sum(vals, Decimal(0))


def _local_day(cfg: Config, ts: int) -> date:
    return datetime.fromtimestamp(ts, cfg.tz).date()


def load_lots_and_disposals(cfg: Config) -> tuple[list[Lot], list[Disposal]]:
    c = db.get()
    lots = [
        Lot(txid=r["txid"], ts=r["ts"], day=_local_day(cfg, r["ts"]), amount=r["amount"],
            price=Decimal(r["price_eur"]) if r["price_eur"] else None, remaining=r["amount"])
        for r in c.execute("SELECT * FROM inflows WHERE kind='block' ORDER BY ts, txid")
    ]
    disposals = [
        Disposal(id=r["id"], ts=r["ts"], day=_local_day(cfg, r["ts"]), amount=r["amount"], kind=r["kind"],
                 proceeds=Decimal(r["proceeds_eur"]) if r["proceeds_eur"] else None,
                 txid=r["txid"] or "", note=r["note"] or "")
        for r in c.execute("SELECT * FROM disposals ORDER BY ts, id")
    ]
    for d in disposals:
        _consume(lots, d)
    return lots, disposals


def _consume(lots: list[Lot], d: Disposal) -> None:
    need = d.amount
    for lot in lots:
        if need <= 0:
            break
        if lot.ts > d.ts or lot.remaining <= 0:
            continue
        take = min(lot.remaining, need)
        lot.remaining -= take
        if d.kind == "own":
            lot.transferred += take
        need -= take
        share = Decimal(take) / Decimal(d.amount)
        proceeds = None if d.proceeds is None or d.kind == "own" else d.proceeds * share
        d.matches.append(Match(lot=lot, amount=take, cost=lot.cost_of(take), proceeds=proceeds,
                               taxable=(d.kind != "own" and d.day < lot.free_from)))
    d.shortfall = max(need, 0)


def sale_calc(cfg: Config, amount_xmr: Decimal, sale_day: date, price_eur: Decimal) -> dict:
    """FIFO-Simulation einer geplanten Veräußerung aus dem aktuellen Bestand."""
    lots, _ = load_lots_and_disposals(cfg)
    need = int((amount_xmr * PICO).to_integral_value())
    rows = []
    for lot in lots:
        if need <= 0:
            break
        if lot.remaining <= 0:
            continue
        take = min(lot.remaining, need)
        need -= take
        proceeds = xmr(take) * price_eur
        cost = lot.cost_of(take)
        taxable = sale_day < lot.free_from
        rows.append({"lot": lot, "amount": take, "proceeds": proceeds, "cost": cost,
                     "gain": None if cost is None else proceeds - cost, "taxable": taxable})
    tax_gain = [r["gain"] for r in rows if r["taxable"]]
    free_gain = [r["gain"] for r in rows if not r["taxable"]]
    return {
        "rows": rows,
        "shortfall": max(need, 0),
        "taxable_gain": None if any(g is None for g in tax_gain) else sum(tax_gain, Decimal(0)),
        "free_gain": None if any(g is None for g in free_gain) else sum(free_gain, Decimal(0)),
        "taxable_amount": sum((r["amount"] for r in rows if r["taxable"]), 0),
        "free_amount": sum((r["amount"] for r in rows if not r["taxable"]), 0),
        "next_free": min((r["lot"].free_from for r in rows if r["taxable"]), default=None),
    }


def year_range(cfg: Config, year: int) -> tuple[int, int]:
    start = datetime(year, 1, 1, tzinfo=cfg.tz)
    end = datetime(year + 1, 1, 1, tzinfo=cfg.tz)
    return int(start.timestamp()), int(end.timestamp())


def inflows_in_year(cfg: Config, year: int, kind: str = "block") -> list[dict]:
    a, b = year_range(cfg, year)
    out = []
    for r in db.get().execute("SELECT * FROM inflows WHERE kind=? AND ts>=? AND ts<? ORDER BY ts", (kind, a, b)):
        price = Decimal(r["price_eur"]) if r["price_eur"] else None
        out.append({
            "txid": r["txid"], "height": r["height"], "ts": r["ts"],
            "dt": datetime.fromtimestamp(r["ts"], cfg.tz),
            "amount": r["amount"], "price": price,
            "value": None if price is None else xmr(r["amount"]) * price,
            "source": r["price_source"] or "",
        })
    return out


def power_by_month(cfg: Config, year: int) -> list[dict]:
    rows = db.get().execute(
        """SELECT substr(day,1,7) AS month, device, SUM(mining_seconds) AS secs, SUM(kwh) AS kwh,
                  SUM(cost_eur) AS cost, SUM(hr_sum) AS hr_sum, SUM(hr_n) AS hr_n
           FROM power_daily WHERE day >= ? AND day < ? GROUP BY month, device ORDER BY month, device""",
        (f"{year}-01-01", f"{year + 1}-01-01")).fetchall()
    return [_power_extras(r) for r in rows]


def _power_extras(r) -> dict:
    """Ø Hashrate sowie effektive Watt und ct/kWh aus den festgeschriebenen Tageswerten."""
    d = dict(r)
    secs, kwh, cost = d.get("secs") or 0, d.get("kwh") or 0.0, d.get("cost") or 0.0
    d["hashrate"] = (d["hr_sum"] / d["hr_n"]) if d.get("hr_n") else 0.0
    d["watts_eff"] = (kwh * 3_600_000 / secs) if secs else None
    d["tariff_eff"] = (cost / kwh * 100) if kwh else None
    return d


def power_by_device(cfg: Config, year: int) -> list[dict]:
    rows = db.get().execute(
        """SELECT device, SUM(mining_seconds) AS secs, SUM(kwh) AS kwh, SUM(cost_eur) AS cost,
                  SUM(hr_sum) AS hr_sum, SUM(hr_n) AS hr_n
           FROM power_daily WHERE day >= ? AND day < ? GROUP BY device ORDER BY device""",
        (f"{year}-01-01", f"{year + 1}-01-01")).fetchall()
    return [_power_extras(r) for r in rows]


def year_summary(cfg: Config, year: int) -> dict:
    infl = inflows_in_year(cfg, year)
    missing = sum(1 for i in infl if i["price"] is None)
    # je Zufluss auf Cent gerundet (wie im Bericht ausgewiesen), dann summiert
    income = sum((eur(i["value"]) for i in infl if i["value"] is not None), Decimal(0))
    amount = sum(i["amount"] for i in infl)
    power = power_by_device(cfg, year)
    power_cost = Decimal(str(sum(p["cost"] or 0 for p in power)))
    power_kwh = sum(p["kwh"] or 0 for p in power)
    result = income - power_cost

    _, disposals = load_lots_and_disposals(cfg)
    disp_year = [d for d in disposals if d.day.year == year]
    gains = [d.taxable_gain for d in disp_year if d.kind != "own"]
    gains_known = all(g is not None for g in gains)
    gain_23 = sum((g for g in gains if g is not None), Decimal(0))

    other_in = inflows_in_year(cfg, year, kind="in")

    return {
        "year": year,
        "inflows": infl, "inflow_count": len(infl), "inflow_amount": amount,
        "income": eur(income), "missing_prices": missing,
        "power": power, "power_cost": eur(power_cost), "power_kwh": power_kwh,
        "result": eur(result),
        "under_freigrenze_22": eur(result) < FREIGRENZE_22_3,
        "disposals": disp_year, "gain_23": eur(gain_23), "gain_23_complete": gains_known,
        "under_freigrenze_23": eur(gain_23) < FREIGRENZE_23,
        "other_inflows": other_in,
    }


def holdings(cfg: Config) -> dict:
    lots, _ = load_lots_and_disposals(cfg)
    today = datetime.now(cfg.tz).date()
    rem = [l for l in lots if l.remaining > 0]
    free = sum(l.remaining for l in rem if today >= l.free_from)
    cost = sum((l.cost_of(l.remaining) for l in rem if l.price is not None), Decimal(0))
    return {"lots": lots, "remaining": sum(l.remaining for l in rem), "free_now": free,
            "locked": sum(l.remaining for l in rem) - free, "cost": eur(cost),
            "next_free": min((l.free_from for l in rem if today < l.free_from), default=None)}
