# Architecture

🌐 [Deutsch](../de/architecture.md) · **English** · [Français](../fr/architecture.md) · [Español](../es/architecture.md)

## Components

| Component | Runs on | Purpose |
|---|---|---|
| **monerod** (`ghcr.io/sethforprivacy/simple-monerod`) | NAS | Your own Monero node, pruned. Verifies every block, provides block templates to P2Pool and data to the wallet |
| **p2pool** (`ghcr.io/sethforprivacy/p2pool`) | NAS | Decentralized pool, **mini** sidechain, `--light-mode`. Pays out directly in the Monero block to the mining address |
| **XMRig** | Computers (macOS/Linux) | Computes RandomX, connects to P2Pool via Stratum; read-only HTTP API for the ledger |
| **wallet-rpc** (`monero-wallet-rpc` in the ledger image) | NAS | View-only wallet from address + view key, synchronized against your own node |
| **xmr-ledger** (`ghcr.io/nexovaanalytics-oss/xmr-ledger`) | NAS | Inflows, prices, power tracking, lots/FIFO, dashboard, Excel report |
| **Mining wallet** (`monero-wallet-cli`) | one computer | A separate wallet used only for mining; keep the seed offline, the spend key stays there |

## Network and ports

| Port | Service | Reachable from |
|---|---|---|
| 18080/tcp | monerod P2P | Internet outbound; inbound only with port forwarding (optional) |
| 18089/tcp | monerod restricted RPC | LAN (wallets, P2Pool, wallet-rpc, ledger) |
| 18084/tcp | monerod ZMQ | Docker-internal only |
| 3333/tcp | P2Pool Stratum | LAN (miners) |
| 37888/tcp | P2Pool P2P (mini) | Internet outbound |
| 18082/tcp | wallet-rpc | Docker-internal only, no published port |
| 8090/tcp | Ledger dashboard | LAN, Basic Auth |
| 18000/tcp | XMRig API on the computers | LAN, bearer token, read-only |

**Never** expose Stratum, RPC or the dashboard to the internet via port forwarding. If the NAS firewall is
active, allow 3333, 8090 and, if needed, 18089 only for your own LAN subnet.

## Ledger data flows

```
                 every 60 s                        every 120 s
XMRig API (computers) ────▶ miners.py ──▶ power_daily / power_samples
                                         (mining time × watts × tariff, frozen at record time)
                                         + activity_hourly (hourly values, analysis only)
monerod (own node, hourly) ──▶ network.py ──▶ network_samples (difficulty, block reward)

wallet-rpc ──────────────▶ walletsync.py ──▶ inflows  (coinbase = mining inflow, otherwise "other receipt")
                                                │
CoinGecko (every 10 min,  ──▶ prices.py ──▶ price_points ──▶ price per inflow (nearest 5-min value,
 last 24 h, unrelated                                         else daily price, else manual)
 to payouts)

Dashboard (outflows entered by hand) ──▶ disposals ──▶ ledger.py: lots, FIFO, § 23 holding periods, annual summary
                                                          └──▶ report.py: Excel / CSV
```

## Files on the NAS (Synology example)

```
/volume1/docker/monero/
├── compose.yaml          # from deploy/nas/compose.yaml
├── .env                  # XMR_ADDRESS, LEDGER_IMAGE, LEDGER_VERSION (keep private)
└── ledger/
    ├── data/             # config.toml (view key!), ledger.sqlite, kurse_manuell.csv  → back up
    └── wallets/          # view-only wallet file, can be recreated from the view key at any time
```

Blockchain and P2Pool data live in Docker volumes (`bitmonero`, `p2pool-data`).

## A note on hosting

Many hosting and cloud providers prohibit mining and running blockchain nodes in their terms of service. Run the
stack at home, or check your provider's terms first.
