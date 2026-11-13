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
| `[power]` | `poll_seconds`, `nas_extra_watts` (0 = don't count the NAS), `[[power.tariff]]` with `valid_from`, `ct_per_kwh` |
| `[[miner]]` | per computer: `name`, `url` (`http://IP:18000`), `token`, `watts` (extra power draw), `note` (measurement) |

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
| **Zuflüsse** (inflows) | All payouts with price and price source; other receipts listed separately |
| **Strom** (electricity) | Mining hours, avg. watts, kWh, avg. ct/kWh, cost per device and month, plus totals across all devices (year and per month) |
| **Lose** (lots) | FIFO lots with acquisition cost and **steuerfrei ab** (tax-free from) date |
| **Abgänge** (outflows) | Record/delete transfers out of the mining wallet |
| **Verkaufs-Rechner** (sale calculator) | Simulate a planned sale/exchange (nothing is stored) |

`/health` answers `ok` without a password (Docker healthcheck).

**Refresh:** While the tab is open, the overview fetches new values every 30 s without reloading the page
(`/api/live`, JSON, same login; paused in a background tab). Next to the year it shows how old the last fetch is,
or "Verbindung verloren" (connection lost). Without JavaScript the overview reloads every 2 minutes. The ledger
collects the data itself in the background: machines every `poll_seconds` (default 60 s), wallet every 120 s,
price history every 10 minutes.

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
| `ledger.py` | Lots, FIFO, holding periods, annual summary, sale calculator |
| `report.py` | Excel and CSV export |
| `web.py` | Dashboard, forms, downloads, auth, CSRF protection |
| `version.py` | Version info from build args |

Tests: `python -m pytest -q ledger/tests` (fake wallet, fake XMRig, fake prices – no internet required).

## Limitations

- CoinGecko (free, no guarantee); historical prices via the free API go back only about one year.
- Mining time only counts while the ledger is running and can reach the computer (costs tend to be
  under- rather than overstated).
- Network fees are not deducted in the sale calculator.
- Dashboard over HTTP: the password travels unencrypted within the LAN (HTTPS via reverse proxy is on the
  [roadmap](../../ROADMAP.md)).
- The tax logic implements **German** rules (see [Tax methodology](tax-methodology.md)); profiles for other
  countries are on the roadmap.
