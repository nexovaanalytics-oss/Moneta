# Moneta

**Mint your own Monero at home.**
Your NAS runs the node and P2Pool, your MacBooks do the hashing – and the XMR-Ledger keeps tax-ready books of
every payout.

🌐 **English** · [Deutsch](README.de.md) · [Français](README.fr.md) · [Español](README.es.md)

[![License: EUPL-1.2](https://img.shields.io/badge/license-EUPL--1.2-blue.svg)](LICENSE)
[![ledger CI](https://github.com/nexovaanalytics-oss/Moneta/actions/workflows/ledger.yml/badge.svg)](https://github.com/nexovaanalytics-oss/Moneta/actions/workflows/ledger.yml)
[![Docs: DE · EN · FR · ES](https://img.shields.io/badge/docs-DE%20%C2%B7%20EN%20%C2%B7%20FR%20%C2%B7%20ES-informational.svg)](docs/README.md)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

> Named after Juno Moneta, whose temple on Rome's Capitoline Hill housed the city's mint – the root of
> "money", "mint" and, via Esperanto, "Monero".

```
Computer 1 (e.g. MacBook Pro) ─┐                         NAS (e.g. Synology DS920+)
Computer 2 (e.g. MacBook Air) ─┼── XMRig ── Stratum ──▶ p2pool (mini) ──▶ monerod (pruned) ──▶ Monero network
                               │                                             ▲
                               └── XMRig API ◀── xmr-ledger ── wallet-rpc ───┘
                                                     │  (view key, read-only)
                                                Dashboard :8090 · Excel annual report
```

## Why Moneta?

- **No middlemen.** Your own node plus P2Pool: no pool operator, no account, no pool fee. Payouts land directly
  in your wallet inside the Monero blocks the pool finds.
- **Hardware you already own.** A NAS that is running anyway, plus the laptops on your desk.
- **Privacy by design.** The server only gets a view-only wallet – the spend key never leaves your computer.
  Price lookups never reveal when you were paid.
- **Books that add up.** Every payout with its EUR price at receipt, electricity cost from measured watts ×
  logged mining time, FIFO lots with holding-period dates, and an Excel annual report.
- **Honest numbers.** At typical European electricity prices, home mining is a hobby, not an investment –
  Moneta shows you exactly what it costs and what it brings in.

## XMR-Ledger

- **Inflows:** every P2Pool payout via a view-only wallet (view key) on your own node
- **Price at receipt** from a locally stored 5-minute price history – the price provider never learns your
  payout times
- **Electricity costs** from measured extra power draw × automatically logged mining time
- **FIFO lots** with acquisition cost and "tax-free from" date (German § 23 EStG)
- **Dashboard**, **Excel annual report** (incl. exemption-threshold checks), **sale calculator**
- Python 3.12, standard library + openpyxl only; image `ghcr.io/nexovaanalytics-oss/xmr-ledger`

The dashboard and the Excel report are currently in **German**; the documentation is available in four
languages. The tax logic implements **German** rules – see the roadmap for other countries.

## Repository layout

| Folder | Contents |
|---|---|
| [`ledger/`](ledger/) | XMR-Ledger: Python app, Dockerfile, tests |
| [`deploy/nas/`](deploy/nas/) | `compose.yaml` and `.env.example` for the NAS stack |
| [`deploy/mac/`](deploy/mac/) | XMRig start script, power measurement |
| [`docs/`](docs/README.md) | Documentation in German, English, French and Spanish |

## Documentation

- [Architecture](docs/en/architecture.md) – components, ports, data flows
- [NAS setup](docs/en/setup-nas.md) · [Computer setup (macOS)](docs/en/setup-mac.md)
- [Using the XMR-Ledger](docs/en/ledger.md) · [Tax methodology](docs/en/tax-methodology.md)
- [Operations: updates, releases, backup, troubleshooting](docs/en/operations.md)
- [Design decisions](docs/en/design-decisions.md)

## Quick start

1. Create a mining wallet, note its primary address and view key ([computer setup](docs/en/setup-mac.md#5-mining-wallet))
2. On the NAS, create `compose.yaml`, `.env` and `ledger/data/config.toml`, then start the stack ([NAS setup](docs/en/setup-nas.md))
3. Let the node sync (several days), then start XMRig with `deploy/mac/xmrig-start.sh`
4. Open the dashboard at `http://<NAS-IP>:8090`

Development: `pip install -r ledger/requirements.txt pytest && python -m pytest -q ledger/tests`

## 🤝 Join in!

Moneta started as a hobby project and is now open to everyone. Whether you mine on a Raspberry Pi, know the tax
rules in Austria, France or Spain, or just found a typo – you are welcome here. Issues and pull requests are
welcome in **English, German, French or Spanish**.

Good places to start:

- 🌍 **Translate the dashboard and the Excel report** (EN/FR/ES and more)
- 🧾 **Add a tax profile for your country**
- 📊 **Share hashrate and power numbers** for your device – one issue form, no code needed
- 🐧 **Guides** for Linux, Windows (WSL2) and other NAS systems
- 🧩 **arm64 image** for the Raspberry Pi and ARM-based NAS devices

→ [Roadmap](ROADMAP.md) · [Contributing guide](CONTRIBUTING.md) ·
[Good first issues](https://github.com/nexovaanalytics-oss/Moneta/labels/good%20first%20issue) ·
[Code of conduct](CODE_OF_CONDUCT.md)

## Important notes

- **Not tax or legal advice.** The ledger implements the position of the German tax administration (BMF circular
  of 6 March 2025); how your individual case is classified is up to you and your advisor.
- **No warranty** for prices, calculations and reports – check results before using them.
- **Economics:** at typical European electricity prices, home mining is mostly a hobby, not an investment.
- **Regulation:** from 10 July 2027, EU-regulated crypto-asset service providers may no longer support privacy
  coins such as Monero (AMLR). Check the rules that apply to you.
- **Hosting:** many hosting providers prohibit mining and blockchain nodes – run it at home or check their terms.
- Please report security issues privately: [SECURITY.md](SECURITY.md).

## License

Copyright © 2026 Moneta contributors.
Licensed under the **European Union Public Licence v. 1.2** ([LICENSE](LICENSE), SPDX: `EUPL-1.2`).
Official versions in all EU languages:
https://interoperable-europe.ec.europa.eu/collection/eupl/eupl-text-eupl-12
Third-party software and data sources: [THIRD_PARTY.md](THIRD_PARTY.md).
