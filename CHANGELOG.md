# Changelog

Per component, newest first. Ledger releases are published as Git tag `ledger-vX.Y.Z`.
Contributors: add user-facing changes under "Unreleased".

## Unreleased

**ledger**
- Dashboard overview updates live: every 30 s via the new read-only endpoint `GET /api/live` (JSON, same Basic
  Auth) without reloading the page; paused while the tab is hidden; status shows the age of the last fetch or
  "connection lost". The full-page reload every 2 minutes remains as a fallback without JavaScript.
- Totals across all devices: the device table on the overview gets a "Gesamt" row (devices mining, combined
  hashrate, combined extra power of the mining devices incl. NAS if configured; also in `/api/live` as
  `totals`); the electricity page gets a sum row per device and a new table "Je Monat, alle Geräte".
- New page **Auswertung** (analysis) for any time range (presets: last night, 24 h, 7/30 days, month, year, or
  from–to): per device time mining/paused/unreachable with a timeline, avg./max. hashrate, hashes, kWh and cost;
  expected value (hashes ÷ difficulty × block reward) compared with the actual payouts; per-day table; CSV export.
  Display only – the report and tax figures still come from the inflows and electricity pages.
- New table `activity_hourly` (DB schema v3, additive): hourly values per device, kept indefinitely, because
  per-minute values are deleted after 30 days. Existing per-minute values are copied over once on first start.
- New table `network_samples`: difficulty and block reward, one value per hour, from your own node's restricted
  RPC (`[node] rpc_url`, default `http://monerod:18089/json_rpc`; empty disables it). Missing hours are fetched
  once from block headers. No external requests.
- The current XMR price card shows the time of the price point ("Stand HH:MM").
- Price history (last 24 h, 5-minute points) is fetched every 10 min instead of every 30 min. Still a fixed
  interval without reference to payouts; price matching per inflow is unchanged.

**deploy/mac**
- New installer `deploy/mac/install.sh`: installs Homebrew and XMRig if needed, asks for pool address and threads,
  creates or takes over the API token, sets up XMRig as launchd agent `moneta.xmrig` (log, restart after a crash,
  optional autostart at login), allows `xmrig` in the macOS firewall on request and prints a ready-made
  `[[miner]]` block for `config.toml`. Safe to run again; `--uninstall` removes it.
- New menu bar app **Moneta Miner** (macOS 13+, SwiftUI, no dependencies): start/stop, threads, autostart,
  hashrate, paused state and pool connection from the local XMRig API. Built locally by the installer with
  `swiftc`, so no Gatekeeper prompt and no Apple developer account.
- New `deploy/mac/moneta-miner.sh` to control the agent from the terminal (`start`, `stop`, `status`, `threads`,
  `autostart`, `log`).
- `xmrig-start.sh`: reads the thread count from `~/.config/moneta/threads`, finds Homebrew's `xmrig` without
  `PATH` (launchd), disables colours when logging, and no longer requires `caffeinate` (Linux).
- Docs: quick setup in `setup-mac.md`, design decision D-09 (all four languages).

## project – 2026-11-13: first public release

- Published under EUPL-1.2.
- Documentation in German, English, French and Spanish (`docs/<de|en|fr|es>/`, German is the reference).
- README, contributing guide and code of conduct (Contributor Covenant 3.0) in four languages; roadmap; issue
  forms (bug, idea, device measurement, translation) and pull request template.

## ledger 1.1.0 – 2026-11-13

Result of the code review.

**Privacy**
- Prices are matched from a locally stored 5-minute history (the last 24 h, fetched every 30 min).
  CoinGecko no longer learns payout times; the daily-price fallback only transmits the date.
- Prices are only fetched for mining inflows, not for other receipts.

**Security**
- CSRF protection: forms (record/delete outflows) only accepted with the dashboard's Origin/Referer.
- The year parameter is validated (400 instead of 500 on invalid input).

**Correctness**
- Annual income = sum of the per-inflow values rounded to the cent (matches the report).
- The electricity view shows effective avg. watts and avg. ct/kWh from the frozen values instead of "last value".

**Publication**
- License EUPL-1.2 (`LICENSE`, SPDX identifiers in all source files); `THIRD_PARTY.md`, `SECURITY.md`.
- Monero license text (BSD-3-Clause) as well as `LICENSE`/`THIRD_PARTY.md` are included in the image under
  `/usr/share/doc/`.
- Build context is the repository root (`docker build -f ledger/Dockerfile .`).
- Docs, examples and scripts without personal environment data; `xmrig-start.sh` reads the pool address from
  `~/.config/moneta/pool`.

**Operations**
- Database migrations via `PRAGMA user_version` (existing v1.0.0 databases are carried over).
- `/health` endpoint and Docker healthcheck; time zone Europe/Berlin in the container.
- Version info (version + commit) in the log, dashboard footer and Excel report.
- XMRig API: fallback to `/1/summary`, warning on a rejected token, warning for `watts = 0`.
- Database connections of web requests are closed after each request.
- Image built by GitHub Actions and published to `ghcr.io/nexovaanalytics-oss/xmr-ledger`.

## ledger 1.0.0 – 2026-11-11

First version: inflows via a view-only wallet, prices (CoinGecko), power tracking via the XMRig API, lots/FIFO,
dashboard, Excel annual report, sale calculator. Built locally, not published.
