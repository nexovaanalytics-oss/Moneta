# Architektur

🌐 **Deutsch** · [English](../en/architecture.md) · [Français](../fr/architecture.md) · [Español](../es/architecture.md)

## Komponenten

| Komponente | Läuft auf | Aufgabe |
|---|---|---|
| **monerod** (`ghcr.io/sethforprivacy/simple-monerod`) | NAS | Eigener Monero-Node, pruned. Prüft alle Blöcke, liefert Blockvorlagen an P2Pool und Daten an die Wallet |
| **p2pool** (`ghcr.io/sethforprivacy/p2pool`) | NAS | Dezentraler Pool, Sidechain **mini**, `--light-mode`. Zahlt direkt im Monero-Block an die Mining-Adresse aus |
| **XMRig** | Rechner (macOS/Linux) | Rechnet RandomX, verbindet sich per Stratum mit P2Pool; lesende HTTP-API für den Ledger |
| **wallet-rpc** (`monero-wallet-rpc` im Ledger-Image) | NAS | Nur-Lesen-Wallet aus Adresse + View-Key, synchronisiert am eigenen Node |
| **xmr-ledger** (`ghcr.io/nexovaanalytics-oss/xmr-ledger`) | NAS | Zuflüsse, Kurse, Stromerfassung, Lose/FIFO, Dashboard, Excel-Bericht |
| **Mining-Wallet** (`monero-wallet-cli`) | ein Rechner | Eigene Wallet nur fürs Mining; Seed offline aufbewahren, Spend-Key bleibt dort |

## Netz und Ports

| Port | Dienst | Erreichbar |
|---|---|---|
| 18080/tcp | monerod P2P | Internet ausgehend; eingehend nur bei Portfreigabe (optional) |
| 18089/tcp | monerod eingeschränkter RPC | LAN (Wallets, P2Pool, wallet-rpc, Ledger) |
| 18084/tcp | monerod ZMQ | nur Docker-intern |
| 3333/tcp | P2Pool Stratum | LAN (Miner) |
| 37888/tcp | P2Pool P2P (mini) | Internet ausgehend |
| 18082/tcp | wallet-rpc | nur Docker-intern, kein veröffentlichter Port |
| 8090/tcp | Ledger-Dashboard | LAN, Basic Auth |
| 18000/tcp | XMRig-API auf den Rechnern | LAN, Bearer-Token, nur lesend |

Stratum, RPC und Dashboard **nie** per Portfreigabe ins Internet stellen. Bei aktiver Firewall auf der NAS
3333, 8090 und ggf. 18089 nur für das eigene LAN-Subnetz freigeben.

## Datenflüsse des Ledgers

```
                 alle 60 s                         alle 120 s
XMRig-API (Rechner) ──────▶ miners.py ──▶ power_daily / power_samples
                                         (Mining-Zeit × Watt × Tarif, festgeschrieben)
                                         + activity_hourly (Stundenwerte, nur Auswertung)
monerod (eigener Node, stündlich) ──▶ network.py ──▶ network_samples (Difficulty, Blockbelohnung)

wallet-rpc ──────────────▶ walletsync.py ──▶ inflows  (Coinbase = Mining-Zufluss, sonst "sonstiger Zugang")
                                                │
CoinGecko (alle 10 Min.,  ──▶ prices.py ──▶ price_points ──▶ Kurs je Zufluss (nächster 5-Min.-Wert,
 letzte 24 h, ohne Bezug                                      sonst Tageskurs, sonst manuell)
 zu Auszahlungen)

Dashboard (Abgänge von Hand) ──▶ disposals ──▶ ledger.py: Lose, FIFO, § 23-Fristen, Jahresübersicht
                                                   └──▶ report.py: Excel / CSV
```

## Dateien auf der NAS (Beispiel Synology)

```
/volume1/docker/monero/
├── compose.yaml          # aus deploy/nas/compose.yaml
├── .env                  # XMR_ADDRESS, LEDGER_IMAGE, LEDGER_VERSION (geheim halten)
└── ledger/
    ├── data/             # config.toml (View-Key!), ledger.sqlite, kurse_manuell.csv  → sichern
    └── wallets/          # Nur-Lesen-Wallet-Datei, jederzeit aus dem View-Key neu erzeugbar
```

Blockchain und P2Pool-Daten liegen in Docker-Volumes (`bitmonero`, `p2pool-data`).

## Hinweis zum Hosting

Viele Hoster und Cloud-Anbieter untersagen in ihren AGB Mining und den Betrieb von Blockchain-Nodes. Den Stack
daher zu Hause betreiben bzw. vorher die Bedingungen des Anbieters prüfen.
