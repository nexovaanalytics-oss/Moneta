# Tax methodology

🌐 [Deutsch](../de/tax-methodology.md) · **English** · [Français](../fr/tax-methodology.md) · [Español](../es/tax-methodology.md)

> **Not tax or legal advice.** This page describes how the XMR-Ledger calculates and is based on the
> **German** tax administration's position (as of 11/2026). It does not replace a review of your individual case;
> other countries have different rules. The [German version](../de/tax-methodology.md) is authoritative.

The tool provides figures and supporting records; the classification of the individual case is up to the
taxpayer. The basis is the administrative position set out in the German Federal Ministry of Finance circular
(BMF-Schreiben) of 6 March 2025 (IV C 1 - S 2256/00042/064/043, "Einzelfragen zur ertragsteuerrechtlichen
Behandlung bestimmter Kryptowerte", replacing the circular of 10 May 2022; block creation: para. 35 et seq.).

## Inflows (income)

- Income from block creation is – depending on the circumstances – business income (§ 15 EStG) or other income
  from services (§ 22 no. 3 EStG); this also applies to crypto assets received from mining pools.
- Valued at the **market price at the time of receipt** (simplified: when credited to the wallet).
- Implementation: time = block time of the coinbase transaction; price = nearest CoinGecko 5-minute price
  (max. 15 min apart), else the daily price at 00:00 UTC, else manual. The source is stored for each inflow.
- EUR per inflow rounded to the cent, then summed.
- Only coinbase receipts count; other receipts (e.g. change from your own transfers) are listed but not counted
  as income.

## Expenses: electricity (Werbungskosten / Betriebsausgaben)

- Measured **extra power draw** per device × automatically logged **mining time** × **electricity price**.
- Measurement: `powermetrics` load − idle, +10 % power-supply losses, rounded up for RAM; date and method are
  recorded in `config.toml` (`note`) and in the report (sheet **Geräte**, devices).
- Watts and tariff are frozen for each record; later changes only take effect going forward.
- Optional: extra consumption of the NAS (`nas_extra_watts`) – currently 0, since the NAS runs anyway.
- Not included: depreciation of existing hardware (the computers are also used privately).

## Exemption threshold under § 22 no. 3 EStG

The report checks whether the result (income − electricity) is **below €256**. This threshold (Freigrenze, not an
allowance: once reached, the full amount is taxable) applies to all income from services in the year combined.
Losses can only be offset against income under § 22 no. 3 (§ 22 no. 3 sentences 3 and 4 EStG, § 10d applying
accordingly). The intention to make a profit must be assessed separately if the result is permanently negative.

## Disposal (§ 23 (1) sentence 1 no. 2 EStG)

- Every payout counts as an **acquisition**; acquisition cost = value at the time of receipt.
- **FIFO** order of consumption per wallet (the mining wallet).
- **One-year holding period:** "tax-free from" (steuerfrei ab) = the day after one year from receipt has elapsed
  (§§ 187 (1), 188 (2) BGB; 29 Feb → 1 Mar).
- Exchanging into other crypto assets and paying with XMR are also disposals; proceeds = EUR value of what was
  received.
- A transfer to your own wallet is not a disposal; the lots (acquisition cost, date) are shown in the report so
  they can be carried forward in the target wallet.
- Exemption threshold of **€1,000** (§ 23 (3) sentence 5 EStG) for all private disposal transactions in the year.

## Records

- Excel annual report (including the ledger version that produced it), CSV of inflows.
- Wallet export: `export_transfers in output=…` in `monero-wallet-cli`.
- P2Pool evidence: mini.p2pool.observer (enter the address).
- Proof of origin for banks/exchanges: mining address, payouts, electricity costs.

## Regulation

From **10 July 2027** (EU Anti-Money Laundering Regulation, Regulation (EU) 2024/1624, Art. 79), EU-regulated
crypto-asset service providers may no longer maintain accounts for privacy coins such as Monero. Holding in your
own wallet and mining remain permitted; converting to euros would then only be possible in two steps
(decentralized XMR → BTC, then a regulated exchange).

## Other countries

The ledger currently implements German rules only. Tax profiles for other countries (holding periods,
thresholds, cost-basis methods) are on the [roadmap](../../ROADMAP.md) – contributions from people who know
their country's rules are very welcome.
