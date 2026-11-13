# Architecture

🌐 [Deutsch](../de/architecture.md) · [English](../en/architecture.md) · **Français** · [Español](../es/architecture.md)

## Composants

| Composant | S'exécute sur | Rôle |
|---|---|---|
| **monerod** (`ghcr.io/sethforprivacy/simple-monerod`) | NAS | Votre propre nœud Monero, élagué (pruned). Vérifie chaque bloc, fournit les modèles de bloc à P2Pool et les données au portefeuille |
| **p2pool** (`ghcr.io/sethforprivacy/p2pool`) | NAS | Pool décentralisé, sidechain **mini**, `--light-mode`. Paie directement dans le bloc Monero à l'adresse de minage |
| **XMRig** | Ordinateurs (macOS/Linux) | Calcule RandomX, se connecte à P2Pool via Stratum ; API HTTP en lecture seule pour le ledger |
| **wallet-rpc** (`monero-wallet-rpc` dans l'image du ledger) | NAS | Portefeuille en lecture seule à partir de l'adresse + clé de visualisation (view key), synchronisé sur votre nœud |
| **xmr-ledger** (`ghcr.io/nexovaanalytics-oss/xmr-ledger`) | NAS | Entrées, cours, suivi de l'électricité, lots/FIFO, tableau de bord, rapport Excel |
| **Portefeuille de minage** (`monero-wallet-cli`) | un ordinateur | Portefeuille dédié au minage ; conservez la phrase de récupération (seed) hors ligne, la clé de dépense reste sur cet ordinateur |

## Réseau et ports

| Port | Service | Accessible depuis |
|---|---|---|
| 18080/tcp | monerod P2P | Internet sortant ; entrant uniquement avec redirection de port (facultatif) |
| 18089/tcp | monerod RPC restreint | LAN (portefeuilles, P2Pool, wallet-rpc) |
| 18084/tcp | monerod ZMQ | interne à Docker uniquement |
| 3333/tcp | P2Pool Stratum | LAN (mineurs) |
| 37888/tcp | P2Pool P2P (mini) | Internet sortant |
| 18082/tcp | wallet-rpc | interne à Docker uniquement, aucun port publié |
| 8090/tcp | Tableau de bord du ledger | LAN, Basic Auth |
| 18000/tcp | API XMRig sur les ordinateurs | LAN, jeton Bearer, lecture seule |

N'exposez **jamais** Stratum, le RPC ou le tableau de bord sur Internet par redirection de port. Si le pare-feu
du NAS est actif, n'ouvrez 3333, 8090 et, si nécessaire, 18089 qu'à votre sous-réseau local.

## Flux de données du ledger

```
                    toutes les 60 s                    toutes les 120 s
API XMRig (ordinateurs) ──▶ miners.py ──▶ power_daily / power_samples
                                         (temps de minage × watts × tarif, figés à l'enregistrement)

wallet-rpc ──────────────▶ walletsync.py ──▶ inflows  (coinbase = entrée de minage, sinon « autre entrée »)
                                                │
CoinGecko (toutes les 30 min, ──▶ prices.py ──▶ price_points ──▶ cours par entrée (valeur 5 min la plus
 dernières 24 h, sans lien                                       proche, sinon cours du jour, sinon manuel)
 avec les paiements)

Tableau de bord (sorties saisies à la main) ──▶ disposals ──▶ ledger.py : lots, FIFO, délais § 23, synthèse annuelle
                                                                 └──▶ report.py : Excel / CSV
```

## Fichiers sur le NAS (exemple Synology)

```
/volume1/docker/monero/
├── compose.yaml          # depuis deploy/nas/compose.yaml
├── .env                  # XMR_ADDRESS, LEDGER_IMAGE, LEDGER_VERSION (à garder secret)
└── ledger/
    ├── data/             # config.toml (clé de visualisation !), ledger.sqlite, kurse_manuell.csv  → à sauvegarder
    └── wallets/          # fichier du portefeuille en lecture seule, recréable à tout moment depuis la view key
```

La blockchain et les données P2Pool se trouvent dans des volumes Docker (`bitmonero`, `p2pool-data`).

## Remarque sur l'hébergement

De nombreux hébergeurs et fournisseurs cloud interdisent dans leurs conditions générales le minage et
l'exploitation de nœuds blockchain. Faites tourner la pile chez vous, ou vérifiez d'abord les conditions de votre
fournisseur.
