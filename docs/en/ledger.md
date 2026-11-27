# XMR-Ledger

🌐 [Deutsch](../de/ledger.md) · **English** · [Français](../fr/ledger.md) · [Español](../es/ledger.md)

Documents your Monero mining automatically: inflows with prices, electricity costs, FIFO lots, holding
periods; plus a dashboard, an Excel annual report and a sale calculator.
Method and legal basis: [Tax methodology](tax-methodology.md).

> The dashboard and the Excel report are currently **German only**. Below, German UI labels are given in bold
> with an English translation. Translating the UI is at the top of the [roadmap](../../ROADMAP.md) – help welcome!

## Configuration

`ledger/data/config.toml` on the NAS (template: [`ledger/config.example.toml`](../../ledger/config.example.toml),
comments in German). It contains the **view key** – do not share it, never commit it.

| Section | Fields |
|---|---|
| `[wallet]` | `address` (4…), `view_key` (`viewkey` → secret), `restore_height` (block height shortly before the wallet was created), `wallet_password` (any) |
| `[web]` | `port`, `user`, `password` (required) |
| `[prices]` | `coingecko_api_key` (optional; a free demo key raises the rate limit) |
| `[node]` | `rpc_url` of your own node for difficulty and block reward (default `http://monerod:18089/json_rpc`, empty = off) |
| `[pool]` | for new computers: `stratum_host` (empty = the NAS IP), `stratum_port` (default 3333); `pairing` (default `true`) allows pairing with a code; `log` (P2Pool log, default `/p2pool/p2pool.log`) and `sidechain` (`mini`, `nano`, `main`) for [Payout → computer](#payout--computer) |
| `[power]` | `poll_seconds`, `nas_extra_watts` (0 = don't count the NAS), `[[power.tariff]]` with `valid_from`, `ct_per_kwh` |
| `[[miner]]` | optional instead of pairing in the dashboard, per computer: `name`, `url` (`http://IP:18000`), `token`, `watts` (extra power draw), `note` (measurement) |

Check before copying it over:

```bash
python3 -c "import tomllib; c=tomllib.load(open('config.toml','rb')); print(len(c['wallet']['address']), len(c['miner']))"
```

After changes: `sudo docker restart xmr-ledger`.

## Dashboard

`http://<NAS-IP>:8090` (Basic Auth, LAN only).

| Page | Content |
|---|---|
| **Übersicht** (overview) | Holdings, amount sellable tax-free, income/electricity/result for the year, device status with a total row (hashrate and extra power of all mining devices, incl. NAS if set), latest payouts, downloads |
| **Zuflüsse** (inflows) | All payouts with price, price source and „Verursacht von“ (share per computer), table „Je Rechner“ for the year; other receipts listed separately |
| **Strom** (electricity) | Mining hours, avg. watts, kWh, avg. ct/kWh, cost per device and month, plus totals across all devices (year and per month) |
| **Auswertung** (analysis) | Any time range (presets: last night, 24 h, 7/30 days, month, year): per device time mining/paused/unreachable with a timeline, avg./max. hashrate, hashes, kWh, cost, shares and attributed XMR; expected value (hashes ÷ difficulty × block reward) vs. actual payouts; timeline „Shares und Auszahlungen“ with „Verursacht von“; per day; CSV |
| **Lose** (lots) | FIFO lots with acquisition cost and **steuerfrei ab** (tax-free from) date |
| **Abgänge** (outflows) | Record/delete transfers out of the mining wallet |
| **Verkaufs-Rechner** (sale calculator) | Simulate a planned sale/exchange (nothing is stored) |
| **Geräte** (devices) | Pair new computers with a code and approve them, change the extra power draw "from now on" (history), retire |

`/health` answers `ok` without a password (Docker healthcheck).

`/api/moneta` also answers without a password, but only with the service name, version, stratum address and
whether pairing is possible – this is how new computers find the ledger in the home network. Under `economics` it
also returns the figures for the thread choice when measuring: difficulty and block reward from your own node, the
latest local price (at most 2 hours old) and the current tariff, plus revenue per H/s and electricity cost per
watt and day (`null` while the node value or price is missing). `/api/pair`
(pairing code) and `/api/heartbeat` (device token) only accept JSON from computers, see
[Pairing computers](#pairing-computers).

**Refresh:** While the tab is open, the overview fetches new values every 30 s without reloading the page
(`/api/live`, JSON, same login; paused in a background tab). Next to the year it shows how old the last fetch is,
or "Verbindung verloren" (connection lost). Without JavaScript the overview reloads every 2 minutes. The ledger
collects the data itself in the background: machines every `poll_seconds` (default 60 s), wallet every 120 s,
price history every 10 minutes.

## Pairing computers

New computers can be added without an entry in `config.toml`:

1. Dashboard → **Geräte** → "Neuen Rechner koppeln – Code erzeugen". The 6-digit code is valid for 10 minutes
   and only once; after five failed attempts it becomes invalid.
2. The computer registers with the code via `POST /api/pair`: name, XMRig URL (home-network addresses only), API
   token, device profile (model, cores) and – if measured – a suggestion for threads and extra power draw. The
   installer and menu bar app will do this with the next update of `deploy/mac`.
3. The computer appears under **Wartet auf Freigabe** (awaiting approval). Check or enter the extra power draw
   and the measurement note, then **Freigeben** (approve). Only then is it polled; the value is frozen with every
   sample, as for `[[miner]]`.
4. If the extra power draw changes (e.g. a different thread count), save a new value under **Aktive Rechner**:
   it applies from the moment it is saved; earlier samples stay unchanged. The Excel report (sheet "Geräte")
   shows the history with "gültig ab" (valid from). **Stilllegen** (retire) stops polling; history and name stay
   visible.

Paired computers report in with their token via `POST /api/heartbeat`; a changed IP is taken over. Computers
from `[[miner]]` keep working unchanged (changes there still need a container restart).

## Payout → computer

P2Pool pays out by PPLNS: a payout is split across all shares in the window of the last 2160 sidechain blocks
(mini ≈ 6 h, nano ≈ 18 h), weighted by share difficulty. For each payout the ledger therefore shows which of your
computers took part and with what share – under **Zuflüsse** („Verursacht von“, table „Je Rechner“) and under
**Auswertung** (timeline „Shares und Auszahlungen“, columns „Shares“ and „zugeordnet XMR“).

- **exakt** (exact): from the P2Pool log. Every own share is logged with time, difficulty and client address
  (`SHARE FOUND: … client <IP:port>[, user <name>]`), every payout with its block height. The ledger reads the log
  incrementally every 60 s (tables `p2pool_shares`, `p2pool_payouts`). The ledger recognises a share's computer by
  the XMRig login: the installer from `deploy/mac` sets up XMRig with the device name as login
  (`-u <name>`, stored in `~/.config/moneta/name`, taken from the ledger for paired computers). Otherwise the
  client IP from `[[miner]]` or pairing applies.
- **eindeutig** (unambiguous): login `x` and an address that belongs to no computer – typical when P2Pool on the
  Docker network only sees the gateway address. Then the ledger's mining times decide: if only one computer was
  mining at the time of the share (± two polls, hourly after 30 days), it is that computer's. The result is stored
  per share. Requires all computers on the pool to be known to the ledger.
- **teilweise** (partial): the log only starts within this payout's window.
- **geschätzt** (estimated): if several computers were mining at the time of a share, it is split by their
  hashrate at that moment (hollow diamond in the chart). Without shares from the log (log missing or starts later)
  the split follows the hash share over the whole window. No computer mining according to the ledger: „unbekannt“.

**Enable:** the `ledger` service gets the P2Pool volume read-only (`deploy/nas/compose.yaml`):

```yaml
    volumes:
      - ./ledger/data:/data
      - p2pool-data:/p2pool:ro
```

Then replace `compose.yaml` on the NAS and run `sudo docker compose -p monero-pool up -d`. Without the volume
everything keeps working as before, only „geschätzt“. **Past payouts:** P2Pool does not rotate its log itself; as
long as `p2pool.log` has not been deleted, the ledger reads the whole history on first start and attributes older
payouts exactly as well.

Display only: inflows, prices, report and tax treatment are unchanged; for tax purposes the whole payout still
counts. External services such as p2pool.observer are not queried, because that would link the mining address to
your IP.

## Usage

- **Outflows:** a view-only wallet cannot see outgoing transfers. Record every transfer: amount = amount sent to
  others + network fee (do not count change); type sale/exchange, payment, or transfer to your own wallet; for
  sale/exchange/payment, the EUR value received.
- **Missing or wrong price:** `ledger/data/kurse_manuell.csv`, one line per entry, `TXID;price` or
  `YYYY-MM-DD;price` (decimal comma allowed). Applies only to inflows without a stored price.
- **Electricity price changes:** add a new `[[power.tariff]]` block with `valid_from`, restart the container.
- **Annual report:** Übersicht → **Excel-Bericht** (sheets: overview with exemption thresholds, inflows,
  electricity, devices, lots, outflows, other receipts). The overview names the ledger version that produced it.

## Code structure (`ledger/app/`)

| Module | Purpose |
|---|---|
| `main.py` | Startup, threads, signals |
| `config.py` | Read and validate `config.toml` |
| `db.py` | SQLite, migrations (`PRAGMA user_version`), per-thread connections |
| `walletsync.py` | wallet-rpc: create/open wallet, read incoming transfers, clean up after reorgs |
| `prices.py` | 5-minute price history, price matching, daily-price fallback, manual prices |
| `miners.py` | Query the XMRig API, record mining time and costs |
| `devices.py` | Paired computers: pairing code, registration, approval, watt history, heartbeat |
| `activity.py` | Hourly values per device, analysis over time ranges |
| `shares.py` | Read the P2Pool log, attribute payouts to computers (display only) |
| `network.py` | Difficulty and block reward from your own node |
| `ledger.py` | Lots, FIFO, holding periods, annual summary, sale calculator |
| `report.py` | Excel and CSV export |
| `web.py` | Dashboard, forms, downloads, auth, CSRF protection |
| `version.py` | Version info from build args |

Tests: `python -m pytest -q ledger/tests` (fake wallet, fake XMRig, fake prices – no internet required).

## Limitations

- Analysis: per-minute values (with timeline) are kept for 30 days, hourly values after that. Hashes = reported
  hashrate × poll interval (approximation); the expected value ignores uncles/orphans. Display only, not a tax basis.
- Payout → computer: the window is time-based (2160 × block time) and so approximates the PPLNS window; uncles
  are ignored. P2Pool behind Docker's port proxy only sees the gateway address; the XMRig login is
  what counts then. Shares from before that are attributed via mining times.
- CoinGecko (free, no guarantee); historical prices via the free API go back only about one year.
- Mining time only counts while the ledger is running and can reach the computer (costs tend to be
  under- rather than overstated).
- Network fees are not deducted in the sale calculator.
- Dashboard over HTTP: the password travels unencrypted within the LAN (HTTPS via reverse proxy is on the
  [roadmap](../../ROADMAP.md)).
- The tax logic implements **German** rules (see [Tax methodology](tax-methodology.md)); profiles for other
  countries are on the roadmap.
- Pairing: token and device details travel unencrypted within the LAN, like the dashboard password. Without a
  valid code no computer can register, and without approval none is recorded.
