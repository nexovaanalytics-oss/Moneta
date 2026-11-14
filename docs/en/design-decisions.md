# Design decisions

🌐 [Deutsch](../de/design-decisions.md) · **English** · [Français](../fr/design-decisions.md) · [Español](../es/design-decisions.md)

Why Moneta is built the way it is. Add new entries at the top (date, context, decision, consequences).
The [German version](../de/design-decisions.md) is the reference.

### D-10 · 2026-11-14 – Pairing new computers with a code, approval in the dashboard
New computers should join without manual edits to `config.toml`. The ledger acts as the control point: it answers
`GET /api/moneta` without a password (service, version, stratum address only) so the installer and app can find it
in the home network; Bonjour/mDNS is ruled out because the container cannot multicast from the bridge network.
Pairing uses a 6-digit code from the dashboard (10 minutes, single use, invalid after five failed attempts) via
`POST /api/pair`. As this is not a browser form, the code, JSON-only bodies and a size limit replace the
same-origin check there; `/api/heartbeat` checks the device token. A paired computer is only polled after approval
with a measured extra power draw – otherwise any device in the LAN could write electricity costs into the
tax-relevant data. Watts are stored as a history with `valid_from` and never overwritten; `[[miner]]` in
`config.toml` remains possible.

### D-09 · 2026-11-13 – Starting the miner from a menu bar app, built locally instead of distributed signed
Computers should be set up without terminal knowledge and started with a button. An installer
(`deploy/mac/install.sh`) sets up XMRig as a launchd agent and builds the menu bar app from source on the computer
itself (`swiftc` from the Command Line Tools, which Homebrew needs anyway). Locally built programs carry no
quarantine attribute, so Gatekeeper does not prompt, and neither a paid Apple developer account nor notarization is
needed. XMRig is not bundled but installed via Homebrew (its own updates); the app only controls the
agent and reads the local XMRig API. The `[[miner]]` entry in `config.toml` deliberately stays a manual step:
watts are frozen with every sample and must be measured first. A signed, notarized app to download remains an
option for later.

### D-08 · 2026-11-13 – Multilingual and open to contributors
Moneta should be usable beyond the German-speaking world and invite people to join in. The project language for
community files (README, CONTRIBUTING, CHANGELOG, SECURITY, templates) is English; README, CONTRIBUTING and the
code of conduct are also available in German, French and Spanish. The documentation lives in
`docs/<de|en|fr|es>/` with identical file names; where versions differ, the German version prevails – especially
for the tax methodology, which describes German law. The dashboard and Excel report remain German for now; their
translation is at the top of the [roadmap](../../ROADMAP.md). Code of conduct: Contributor Covenant 3.0.

### D-07 · 2026-11-13 – Published under EUPL-1.2
Copyleft that also covers operation as a web service; official versions in all EU languages; liability and
choice of law under EU law. Third-party licenses in [`THIRD_PARTY.md`](../../THIRD_PARTY.md), Monero license
inside the image.

### D-06 · 2026-11-13 – Image built by GitHub Actions, version pinned deliberately on the server
GitHub Actions tests and builds `ghcr.io/nexovaanalytics-oss/xmr-ledger`. On the server the version is pinned in
`.env` (`LEDGER_VERSION`), no auto-update. Every Excel report names the version that produced it.

### D-05 · 2026-11-13 – Prices matched locally from a 5-minute history
Queries like "price at time X" would reveal payout times to the price provider; combined with the public P2Pool
address, the IP address could be linked to the mining address. Therefore the last 24 h are fetched at a fixed interval
(currently every 10 minutes) and stored locally; matching happens locally (max. 15 min apart). The daily price is only a fallback –
in that case only the date is transmitted.

### D-04 · 2026-11-11 – Electricity cost = measured extra power × logged mining time
A plug-in meter on a laptop also captures charging and normal use. Therefore the extra power draw is measured
once (load − idle, +10 % for the power supply) and the running time is logged automatically via the XMRig API.
Watts and tariff are frozen for each record; configuration changes only take effect going forward.

### D-03 · 2026-11-11 – View-only wallet, outflows entered by hand
The spend key should not be on the server. `monero-wallet-rpc` works with address + view key. Such a wallet
sees incoming but not outgoing transfers: only coinbase receipts count as mining inflows, other receipts (e.g.
change) are listed separately, outflows are entered in the dashboard.

### D-02 · 2026-11-11 – One lot per payout, FIFO
Every payout is an acquisition (acquisition cost = value at receipt); FIFO order of consumption; "tax-free from"
= the day after the one-year period has elapsed (§§ 187 (1), 188 (2) BGB). Details:
[Tax methodology](tax-methodology.md).

### D-01 · 2026-11-11 – Own node + P2Pool on the NAS, computers only hash
Node and pool need storage but hardly any computing power – and the NAS runs anyway. monerod pruned with
`--sync-pruned-blocks`, P2Pool mini with `--light-mode`. The computers only connect via Stratum; any number of
additional computers can join in.
