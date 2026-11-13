# Changelog

Per component, newest first. Ledger releases are published as Git tag `ledger-vX.Y.Z`.
Contributors: add user-facing changes under "Unreleased".

## Unreleased

**ledger**
- Dashboard overview updates live: every 30 s via the new read-only endpoint `GET /api/live` (JSON, same Basic
  Auth) without reloading the page; paused while the tab is hidden; status shows the age of the last fetch or
  "connection lost". The full-page reload every 2 minutes remains as a fallback without JavaScript.
- The current XMR price card shows the time of the price point ("Stand HH:MM").
- Price history (last 24 h, 5-minute points) is fetched every 10 min instead of every 30 min. Still a fixed
  interval without reference to payouts; price matching per inflow is unchanged.

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
