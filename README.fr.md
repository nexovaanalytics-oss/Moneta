# Moneta

**Frappez vos propres Monero, chez vous.**
Votre NAS fait tourner le nœud et P2Pool, vos MacBook calculent – et le XMR-Ledger tient une comptabilité de
chaque paiement, prête pour la déclaration fiscale.

🌐 [English](README.md) · [Deutsch](README.de.md) · **Français** · [Español](README.es.md)

[![Licence : EUPL-1.2](https://img.shields.io/badge/license-EUPL--1.2-blue.svg)](LICENSE)
[![ledger CI](https://github.com/nexovaanalytics-oss/Moneta/actions/workflows/ledger.yml/badge.svg)](https://github.com/nexovaanalytics-oss/Moneta/actions/workflows/ledger.yml)
[![Docs : DE · EN · FR · ES](https://img.shields.io/badge/docs-DE%20%C2%B7%20EN%20%C2%B7%20FR%20%C2%B7%20ES-informational.svg)](docs/README.md)
[![Contributions bienvenues](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.fr.md)

> Nommé d'après Junon Moneta, dont le temple sur le Capitole abritait l'atelier monétaire de Rome – d'où
> « money », « monnaie » et, via l'espéranto, « Monero ».

```
Ordinateur 1 (p. ex. MacBook Pro) ─┐                         NAS (p. ex. Synology DS920+)
Ordinateur 2 (p. ex. MacBook Air) ─┼── XMRig ── Stratum ──▶ p2pool (mini) ──▶ monerod (pruned) ──▶ réseau Monero
                                   │                                             ▲
                                   └── API XMRig ◀── xmr-ledger ── wallet-rpc ───┘
                                                         │  (view key, lecture seule)
                                                    Tableau de bord :8090 · rapport annuel Excel
```

## Pourquoi Moneta ?

- **Sans intermédiaire.** Votre propre nœud plus P2Pool : pas d'opérateur de pool, pas de compte, pas de frais de
  pool. Les paiements arrivent directement dans votre portefeuille, dans les blocs Monero trouvés par le pool.
- **Le matériel que vous avez déjà.** Un NAS qui tourne de toute façon, et les portables sur votre bureau.
- **Confidentialité dès la conception.** Le serveur ne reçoit qu'un portefeuille en lecture seule – la clé de
  dépense ne quitte jamais votre ordinateur. Les requêtes de cours ne révèlent jamais quand vous avez été payé.
- **Des comptes qui tombent juste.** Chaque paiement avec son cours en EUR à la réception, le coût de
  l'électricité calculé à partir des watts mesurés × le temps de minage enregistré, des lots FIFO avec dates de
  fin de détention, et un rapport annuel Excel.
- **Des chiffres honnêtes.** Aux prix européens habituels de l'électricité, le minage à domicile est un loisir,
  pas un placement – Moneta vous montre précisément ce qu'il coûte et ce qu'il rapporte.

## XMR-Ledger

- **Entrées :** chaque paiement P2Pool via un portefeuille en lecture seule (view key) sur votre propre nœud
- **Cours à la réception** issu d'un historique de cours à 5 minutes stocké localement – le fournisseur de cours
  ne connaît jamais vos heures de paiement
- **Coûts d'électricité** = surconsommation mesurée × temps de minage enregistré automatiquement
- **Lots FIFO** avec coût d'acquisition et date « exonéré à partir du » (§ 23 EStG allemand)
- **Tableau de bord**, **rapport annuel Excel** (avec contrôle des seuils d'exonération), **calculateur de vente**
- Python 3.12, bibliothèque standard + openpyxl uniquement ; image `ghcr.io/nexovaanalytics-oss/xmr-ledger`

Le tableau de bord et le rapport Excel sont pour l'instant **en allemand** ; la documentation existe en quatre
langues. La logique fiscale applique les règles **allemandes** – voir la feuille de route pour les autres pays.

## Contenu du dépôt

| Dossier | Contenu |
|---|---|
| [`ledger/`](ledger/) | XMR-Ledger : application Python, Dockerfile, tests |
| [`deploy/nas/`](deploy/nas/) | `compose.yaml` et `.env.example` pour la pile du NAS |
| [`deploy/mac/`](deploy/mac/) | Installateur et application de barre des menus pour XMRig, script de démarrage, mesure de la consommation |
| [`docs/`](docs/README.md) | Documentation en allemand, anglais, français et espagnol |

## Documentation

- [Architecture](docs/fr/architecture.md) – composants, ports, flux de données
- [Installation NAS](docs/fr/setup-nas.md) · [Installation ordinateur (macOS)](docs/fr/setup-mac.md)
- [Utiliser le XMR-Ledger](docs/fr/ledger.md) · [Méthodologie fiscale](docs/fr/tax-methodology.md)
- [Exploitation : mises à jour, versions, sauvegarde, dépannage](docs/fr/operations.md)
- [Décisions de conception](docs/fr/design-decisions.md)

## Démarrage rapide

1. Créer un portefeuille de minage, noter l'adresse principale et la clé de visualisation ([installation ordinateur](docs/fr/setup-mac.md#5-portefeuille-de-minage))
2. Sur le NAS, créer `compose.yaml`, `.env` et `ledger/data/config.toml`, puis démarrer ([installation NAS](docs/fr/setup-nas.md))
3. Laisser le nœud se synchroniser (plusieurs jours), puis configurer l'ordinateur avec `deploy/mac/install.sh` et lancer XMRig depuis la barre des menus
4. Tableau de bord : `http://<IP-NAS>:8090`

Développement : `pip install -r ledger/requirements.txt pytest && python -m pytest -q ledger/tests`

## 🤝 Participez !

Moneta est né comme projet de loisir et est désormais ouvert à toutes et à tous. Que vous miniez sur un
Raspberry Pi, que vous connaissiez les règles fiscales en France, en Belgique ou en Suisse, ou que vous ayez
simplement repéré une coquille – vous êtes les bienvenus. Issues et pull requests bienvenues en **français,
anglais, allemand ou espagnol**.

Pour commencer :

- 🌍 **Traduire le tableau de bord et le rapport Excel** (EN/FR/ES et plus)
- 🧾 **Ajouter un profil fiscal pour votre pays**
- 📊 **Partager hashrate et consommation** de votre appareil – un simple formulaire d'issue, sans code
- 🐧 **Guides** pour Linux, Windows (WSL2) et d'autres NAS
- 🧩 **Image arm64** pour Raspberry Pi et NAS ARM

→ [Feuille de route](ROADMAP.md) · [Guide de contribution](CONTRIBUTING.fr.md) ·
[Good first issues](https://github.com/nexovaanalytics-oss/Moneta/labels/good%20first%20issue) ·
[Code de conduite](CODE_OF_CONDUCT.fr.md)

## Avertissements importants

- **Ni conseil fiscal ni conseil juridique.** Le ledger met en œuvre la doctrine de l'administration fiscale
  allemande (circulaire du BMF du 6 mars 2025) ; la qualification de votre cas vous revient, à vous et à votre
  conseil.
- **Aucune garantie** sur les cours, calculs et rapports – vérifiez les résultats avant de les utiliser.
- **Rentabilité :** aux prix européens habituels de l'électricité, le minage à domicile est surtout un loisir,
  pas un placement.
- **Réglementation :** à partir du 10 juillet 2027, les prestataires de services sur crypto-actifs réglementés
  dans l'UE ne pourront plus proposer de « privacy coins » comme Monero (AMLR). Vérifiez les règles qui
  s'appliquent à vous.
- **Hébergement :** de nombreux hébergeurs interdisent le minage et les nœuds blockchain – faites-le tourner chez
  vous ou vérifiez leurs conditions.
- Signalez les failles de sécurité de manière confidentielle : [SECURITY.md](SECURITY.md).

## Licence

Copyright © 2026 les contributeurs de Moneta.
Sous licence **European Union Public Licence v. 1.2** ([LICENSE](LICENSE), SPDX : `EUPL-1.2`).
Versions officielles dans toutes les langues de l'UE, dont le français :
https://interoperable-europe.ec.europa.eu/collection/eupl/eupl-text-eupl-12
Logiciels tiers et sources de données : [THIRD_PARTY.md](THIRD_PARTY.md).
