# Roadmap

Where Moneta could go next. Nothing here is promised – it is a list of ideas, and **you are invited to pick one**.
Comment on (or open) an issue before you start, so nobody works on the same thing twice.

Labels: 🟢 good first issue · 🟡 help wanted · 🔵 needs design discussion first

## Reach more people

| | Idea | Notes |
|---|---|---|
| 🟡 | **Translate the dashboard and the Excel report** (EN, FR, ES, …) | Move UI strings out of `web.py` / `report.py` into simple per-language files (no new dependency); language chosen in `config.toml`. Sheet and column names in the report as well. |
| 🟢 | **More reference values** for hashrate and power draw | Use the "Device measurement" issue form – no code needed. |
| 🟢 | **Guide: miners on Linux** | XMRig from the package manager, systemd service, power measurement with a metering plug or RAPL. |
| 🟢 | **Guide: other NAS and servers** | QNAP, Unraid, TrueNAS, a plain Debian box – what differs from the Synology guide. |
| 🟢 | **Guide: Windows via WSL2** | Smart App Control blocks XMRig on Windows; document a working WSL2 route. |
| 🟡 | **Translate config comments and script messages** | `ledger/config.example.toml`, `deploy/mac/*.sh` are currently German. |

## Tax and bookkeeping

| | Idea | Notes |
|---|---|---|
| 🔵 | **Tax profiles for other countries** (AT, CH, FR, ES, …) | Make holding periods, exemption thresholds, cost-basis methods (FIFO, average cost, …) and report wording pluggable. Needs people who know their country's rules – and a clear "not tax advice" note per profile. |
| 🔵 | **Currencies other than EUR** | Price history and report in CHF, USD, … |
| 🟡 | **Import outflows from a wallet export** | Parse `export_transfers` CSV instead of entering outflows by hand. |
| 🟢 | **Network fees in the sale calculator** | Currently not deducted. |

## Operations

| | Idea | Notes |
|---|---|---|
| 🟡 | **arm64 image** (Raspberry Pi 5, ARM-based NAS) | Multi-arch build in GitHub Actions; download the matching Monero CLI (`linux-armv8`) with checksum verification. |
| 🟡 | **Signed, notarized download of the menu bar app** | One-click install without Terminal for other users; needs an Apple Developer ID and notarization (see design decision D-09). |
| 🟡 | **Node and P2Pool status in the dashboard** | Sync height, peers, P2Pool shares in the PPLNS window – read-only, LAN only. |
| 🟢 | **Guide: HTTPS via reverse proxy** | e.g. DSM reverse proxy or Caddy in front of the dashboard. |
| 🔵 | **Notifications** | New payout, device offline, sync stalled. Must not leak payout times to third parties – local or self-hosted channels first. |

## Mining

| | Idea | Notes |
|---|---|---|
| 🔵 | **Evaluate merge mining via P2Pool** | Check what current P2Pool versions support and what it would mean for the ledger (second asset, prices, tax). |
| 🔵 | **Bitcoin solo-mining module** | Optional stack for small SHA-256 lottery miners with your own Bitcoin node. |

## Quality

| | Idea | Notes |
|---|---|---|
| 🟢 | **More tests** | Edge cases for FIFO, holding periods around leap years, reorgs, price gaps. |
| 🟡 | **Linting and type checks in CI** | e.g. `ruff` and `mypy` as dev-only tools. |

Have another idea? Open an issue with the "Idea or feature request" form.
