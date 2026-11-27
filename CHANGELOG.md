# Changelog

Per component, newest first. Ledger releases are published as Git tag `ledger-vX.Y.Z`.
Contributors: add user-facing changes under "Unreleased".

## Unreleased

**ledger**
- Payout → computer: the ledger reads the P2Pool log read-only and incrementally (`[pool] log`, default
  `/p2pool/p2pool.log`; `sidechain` = `mini`/`nano`/`main` sets the PPLNS window) and stores your own shares with
  client address and login name. Each payout is split across the shares in its PPLNS window by share difficulty
  and mapped to devices via `[[miner]]`/paired computers (a login matching a device name wins over the IP).
  Labelled „exakt“, „teilweise“ (log starts inside the window) or „geschätzt“ (no log: split by hash share from
  the hourly values). Shown under **Zuflüsse** (column „Verursacht von“, table „Je Rechner“) and **Auswertung**
  (timeline „Shares und Auszahlungen“, columns „Shares“ and „zugeordnet XMR“). Display only – inflows, prices,
  report and tax data are unchanged. Past payouts are attributed as far back as `p2pool.log` reaches. No external
  services are queried (design decision D-12).
- DB schema v5 (additive: `p2pool_shares`, `p2pool_payouts`).
- Payout → computer behind Docker: P2Pool behind Docker's port proxy only sees the gateway address, so the client
  IP cannot identify a computer. A share's computer now comes from the XMRig login (device name, matched the way
  P2Pool shortens it), then the client IP, then the ledger's mining times at the time of the share: only one
  computer mining → „eindeutig“, several → split by their hashrate at that moment („geschätzt“, hollow diamond in
  the chart). The result is stored per share, since per-minute values are deleted after 30 days. New method label
  „eindeutig“; the table „Je Rechner“ counts it as „exakt/eindeutig“ (design decision D-13).
- DB schema v6 (additive: `p2pool_shares.source`, `p2pool_shares.parts`).

**deploy/nas**
- `compose.yaml`: the `ledger` service mounts `p2pool-data:/p2pool:ro` (for the P2Pool log). Replace
  `compose.yaml` on the NAS when updating and run `docker compose up -d`; without it, payouts are only estimated.
- New `deploy/nas/update-ledger.sh`: deploys a ledger release on the NAS in one step – asks GitHub for the latest
  `ledger-vX.Y.Z` (or takes a given version), asks for confirmation, pulls the image first, backs up the database
  inside the running container (SQLite backup incl. WAL), sets `LEDGER_VERSION` in `.env`, restarts `wallet-rpc`
  and `ledger` and prints the log and rollback steps. `--check` only compares versions. The version stays pinned.

**deploy/mac**
- Fix: the XMRig log `~/Library/Logs/Moneta/xmrig.log` stayed empty under launchd. XMRig only prints its console
  output to a terminal or pipe, not to a redirected file, so the menu bar app's "Log" button showed nothing (e.g.
  no reason for rejected shares). `xmrig-start.sh` now also passes `--log-file` when its output is not a terminal.
  Existing Macs: `git pull`, then run `install.sh` again (or copy `xmrig-start.sh` and restart the miner).
- XMRig logs in to P2Pool with the device name (`-u`, from `~/.config/moneta/name`): the installer asks for it (or
  takes it from pairing), and `moneta-miner.sh heartbeat` keeps it in sync with the ledger. Lets the ledger
  attribute payouts to computers even when P2Pool only sees a Docker address. Existing Macs: `git pull`, then run
  `install.sh` again.
- `einmessen.sh` measures a ladder of steps up to all cores instead of two thread counts (e.g. M4 with 4 + 6 cores:
  3, 4, 7, 10; ascending, no cool-down) and suggests the step with the highest balance of calculated revenue and
  electricity cost, using the figures from the ledger; without them, the best hashrate per watt. The table shows
  every step with revenue, electricity and balance per day. The installer shows "n of N threads" with the reason
  and uses a fresh measurement as the default instead of the old setting.
- Fix: `moneta-miner.sh status` failed without output while XMRig was stopped (launchd agent not loaded), so the
  menu bar app showed "moneta-miner.sh nicht gefunden – install.sh ausführen". The app now also clears a status
  error as soon as the next status query succeeds.
- New installer `deploy/mac/install.sh`: installs Homebrew and XMRig if needed, asks for pool address and threads,
  creates or takes over the API token, sets up XMRig as launchd agent `moneta.xmrig` (log, restart after a crash,
  optional autostart at login), allows `xmrig` in the macOS firewall on request and prints a ready-made
  `[[miner]]` block for `config.toml`. Safe to run again; `--uninstall` removes it.
- New menu bar app **Moneta Miner** (macOS 13+, SwiftUI, no dependencies): start/stop, threads, autostart,
  hashrate, paused state and pool connection from the local XMRig API. Built locally by the installer with
  `swiftc`, so no Gatekeeper prompt and no Apple developer account.
- Menu bar app 1.1 – a live cockpit for this Mac: hashrate next to the menu bar icon (can be switched off), a
  window with the hashrate history of the last 15 min / 1 h / 6 h (Swift Charts, kept in memory only), a state
  timeline (mining/paused/stopped), average and paused time for the window, hashrate per thread, pool latency,
  accepted/rejected stratum shares, power source and thermal state. When XMRig pauses, the app shows why: battery
  mode with battery level, a detected power adapter and running charge limiters such as AlDente (XMRig runs with
  `--pause-on-battery`), plus hints for Low Power Mode and thermal throttling. A "Dashboard" button opens the
  ledger dashboard (pool host, port 8090, or the URL in `~/.config/moneta/dashboard`). Update: `git pull`, then
  run `deploy/mac/install.sh` again.
- CI: new workflow `mac-app` compiles the menu bar app on a macOS runner (Xcode and Command Line Tools only)
  whenever `deploy/mac/MonetaMiner/` changes.
- New `deploy/mac/moneta-miner.sh` to control the agent from the terminal (`start`, `stop`, `status`, `threads`,
  `autostart`, `log`).
- `xmrig-start.sh`: reads the thread count from `~/.config/moneta/threads`, finds Homebrew's `xmrig` without
  `PATH` (launchd), disables colours when logging, and no longer requires `caffeinate` (Linux).
- Docs: quick setup in `setup-mac.md`, design decision D-09 (all four languages).
- Installer finds the XMR ledger in the home network (`GET /api/moneta` on port 8090 across the local /24) and
  takes the pool address from it; `LEDGER=http://<NAS-IP>:8090` skips the search.
- Pairing: the installer asks for the pairing code from the dashboard (**Geräte**) and registers the Mac with
  name, address, token, device profile and – if measured – threads and extra power draw. The ledger records it
  after approval. Without a ledger or code it prints the `[[miner]]` block as before. Requires ledger ≥ 1.3.0.
- `moneta-miner.sh heartbeat` reports IP and threads to the ledger; runs automatically after `start`/`restart`,
  so a changed IP is picked up. `status` shows the ledger and pairing state (`ledger=`, `paired=` in `--plain`).
- New `deploy/mac/profil.sh`: device profile (model, chip, performance/efficiency cores, fanless) and thread
  suggestion from `deploy/mac/profile.tsv` (measured devices) or the rule of thumb – fanless: performance cores
  − 1, with a fan: all cores.
- New `deploy/mac/einmessen.sh`: measures idle and load power (`powermetrics`) and hashrate for two thread
  counts, suggests the best hashrate per watt and writes threads, extra watts and a ready-made note to
  `~/.config/moneta/einmessung.json` (used by installer and pairing).
- Fix: the docs and installer claimed the Homebrew build donates 0 %; like all official XMRig builds it donates at
  least 1 % (`--donate-level 0` is ignored). Corrected in `setup-mac.md` and D-09.

## ledger 1.4.0 – 2026-11-14

- `GET /api/moneta` additionally returns `economics`: difficulty and block reward from your own node, the latest
  local price, the current tariff, and from these the calculated revenue per H/s and electricity cost per watt and
  day – for the thread choice in `einmessen.sh` (design decision D-11). `null` while node value or price is missing.

## ledger 1.3.0 – 2026-11-14

- Pair new computers from the dashboard (new page "Geräte"): generate a 6-digit code (10 min, single use, invalid
  after five failed attempts); the computer registers via `POST /api/pair` and is only polled after approval with a
  measured extra power draw and note. Watts per paired computer are kept as a history (`valid_from`, never
  overwritten; new value applies from now on); computers can be retired. `[[miner]]` in `config.toml` still works.
- `GET /api/moneta` (no password, no sensitive data): lets installers find the ledger in the LAN and returns the
  stratum address (`[pool] stratum_host`, `stratum_port`; `pairing` switches pairing off).
- `POST /api/heartbeat` (device token): paired computers report a changed IP and their thread setting.
- The device list (overview, `/api/live`, polling) is now read live from `config.toml` plus the database – no
  restart after pairing. The Excel sheet "Geräte" shows the watt history with "gültig ab" and the source.
- DB schema v4 (additive: `devices`, `device_watts`).

## ledger 1.2.0 – 2026-11-14

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
