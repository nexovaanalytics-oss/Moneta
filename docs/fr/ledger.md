# XMR-Ledger

🌐 [Deutsch](../de/ledger.md) · [English](../en/ledger.md) · **Français** · [Español](../es/ledger.md)

Documente automatiquement votre minage de Monero : entrées avec cours, coûts d'électricité, lots FIFO, délais de
détention ; avec un tableau de bord, un rapport annuel Excel et un calculateur de vente.
Méthode et base légale : [Méthodologie fiscale](tax-methodology.md).

> Le tableau de bord et le rapport Excel sont pour l'instant **uniquement en allemand**. Ci-dessous, les libellés
> allemands de l'interface sont indiqués en gras avec leur traduction. Traduire l'interface est en tête de la
> [feuille de route](../../ROADMAP.md) – toute aide est la bienvenue !

## Configuration

`ledger/data/config.toml` sur le NAS (modèle : [`ledger/config.example.toml`](../../ledger/config.example.toml),
commentaires en allemand). Il contient la **clé de visualisation** – ne la partagez pas, ne la versionnez jamais.

| Section | Champs |
|---|---|
| `[wallet]` | `address` (4…), `view_key` (`viewkey` → secret), `restore_height` (hauteur de bloc peu avant la création du portefeuille), `wallet_password` (libre) |
| `[web]` | `port`, `user`, `password` (obligatoire) |
| `[prices]` | `coingecko_api_key` (facultatif ; une clé démo gratuite relève la limite de requêtes) |
| `[power]` | `poll_seconds`, `nas_extra_watts` (0 = ne pas compter le NAS), `[[power.tariff]]` avec `valid_from`, `ct_per_kwh` |
| `[[miner]]` | par ordinateur : `name`, `url` (`http://IP:18000`), `token`, `watts` (surconsommation), `note` (mesure) |

Vérifier avant de copier :

```bash
python3 -c "import tomllib; c=tomllib.load(open('config.toml','rb')); print(len(c['wallet']['address']), len(c['miner']))"
```

Après une modification : `sudo docker restart xmr-ledger`.

## Tableau de bord

`http://<IP-NAS>:8090` (Basic Auth, LAN uniquement).

| Page | Contenu |
|---|---|
| **Übersicht** (vue d'ensemble) | Avoirs, montant cessible en franchise d'impôt, revenus/électricité/résultat de l'année, état des appareils, derniers paiements, téléchargements |
| **Zuflüsse** (entrées) | Tous les paiements avec cours et source du cours ; autres entrées listées à part |
| **Strom** (électricité) | Heures de minage, watts moyens, kWh, ct/kWh moyens, coût par appareil et par mois |
| **Lose** (lots) | Lots FIFO avec coût d'acquisition et date **steuerfrei ab** (exonéré à partir du) |
| **Abgänge** (sorties) | Saisir/supprimer les transferts sortant du portefeuille de minage |
| **Verkaufs-Rechner** (calculateur de vente) | Simuler une vente/un échange prévu (rien n'est enregistré) |

`/health` répond `ok` sans mot de passe (healthcheck Docker).

**Actualisation :** tant que l'onglet est ouvert, la vue d'ensemble récupère de nouvelles valeurs toutes les
30 s sans recharger la page (`/api/live`, JSON, même identification ; en pause dans un onglet en arrière-plan).
À côté de l'année, elle indique l'âge de la dernière récupération, ou « Verbindung verloren » (connexion perdue).
Sans JavaScript, la vue d'ensemble se recharge toutes les 2 minutes. Les données elles-mêmes sont collectées par
le ledger en arrière-plan : machines toutes les `poll_seconds` (60 s par défaut), portefeuille toutes les 120 s,
historique des cours toutes les 10 minutes.

## Utilisation

- **Sorties :** un portefeuille en lecture seule ne voit pas les transferts sortants. Saisissez chaque transfert :
  montant = montant envoyé à des tiers + frais de réseau (ne pas compter la monnaie rendue) ; type
  vente/échange, paiement ou transfert vers votre propre portefeuille ; pour une vente/un échange/un paiement, la
  contre-valeur en EUR.
- **Cours manquant ou erroné :** `ledger/data/kurse_manuell.csv`, une ligne par entrée, `TXID;cours` ou
  `AAAA-MM-JJ;cours` (virgule décimale autorisée). Ne s'applique qu'aux entrées sans cours enregistré.
- **Changement du prix de l'électricité :** ajoutez un nouveau bloc `[[power.tariff]]` avec `valid_from`,
  redémarrez le conteneur.
- **Rapport annuel :** Übersicht → **Excel-Bericht** (feuilles : vue d'ensemble avec seuils d'exonération,
  entrées, électricité, appareils, lots, sorties, autres entrées). La vue d'ensemble indique la version du ledger
  qui l'a produit.

## Structure du code (`ledger/app/`)

| Module | Rôle |
|---|---|
| `main.py` | Démarrage, threads, signaux |
| `config.py` | Lire et valider `config.toml` |
| `db.py` | SQLite, migrations (`PRAGMA user_version`), connexions par thread |
| `walletsync.py` | wallet-rpc : créer/ouvrir le portefeuille, lire les entrées, nettoyer après une réorganisation |
| `prices.py` | Historique des cours à 5 minutes, attribution des cours, repli sur le cours du jour, cours manuels |
| `miners.py` | Interroger l'API XMRig, enregistrer le temps de minage et les coûts |
| `ledger.py` | Lots, FIFO, délais, synthèse annuelle, calculateur de vente |
| `report.py` | Export Excel et CSV |
| `web.py` | Tableau de bord, formulaires, téléchargements, authentification, protection CSRF |
| `version.py` | Informations de version issues des arguments de build |

Tests : `python -m pytest -q ledger/tests` (faux portefeuille, faux XMRig, faux cours – pas besoin d'Internet).

## Limites

- CoinGecko (gratuit, sans garantie) ; via l'API gratuite, les cours historiques ne remontent qu'à environ un an.
- Le temps de minage n'est compté que tant que le ledger tourne et joint l'ordinateur (coûts plutôt sous-estimés
  que surestimés).
- Les frais de réseau ne sont pas déduits dans le calculateur de vente.
- Tableau de bord en HTTP : le mot de passe circule en clair dans le LAN (HTTPS via proxy inverse figure dans la
  [feuille de route](../../ROADMAP.md)).
- La logique fiscale applique les règles **allemandes** (voir [Méthodologie fiscale](tax-methodology.md)) ; des
  profils pour d'autres pays sont prévus dans la feuille de route.
