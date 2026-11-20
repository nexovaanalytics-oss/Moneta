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
| `[node]` | `rpc_url` de votre propre nœud pour la difficulté et la récompense de bloc (par défaut `http://monerod:18089/json_rpc`, vide = désactivé) |
| `[pool]` | pour les nouveaux ordinateurs : `stratum_host` (vide = IP du NAS), `stratum_port` (3333 par défaut) ; `pairing` (`true` par défaut) autorise l'appairage par code ; `log` (journal P2Pool, par défaut `/p2pool/p2pool.log`) et `sidechain` (`mini`, `nano`, `main`) pour [Paiement → ordinateur](#paiement--ordinateur) |
| `[power]` | `poll_seconds`, `nas_extra_watts` (0 = ne pas compter le NAS), `[[power.tariff]]` avec `valid_from`, `ct_per_kwh` |
| `[[miner]]` | facultatif, à la place de l'appairage dans le tableau de bord, par ordinateur : `name`, `url` (`http://IP:18000`), `token`, `watts` (surconsommation), `note` (mesure) |

Vérifier avant de copier :

```bash
python3 -c "import tomllib; c=tomllib.load(open('config.toml','rb')); print(len(c['wallet']['address']), len(c['miner']))"
```

Après une modification : `sudo docker restart xmr-ledger`.

## Tableau de bord

`http://<IP-NAS>:8090` (Basic Auth, LAN uniquement).

| Page | Contenu |
|---|---|
| **Übersicht** (vue d'ensemble) | Avoirs, montant cessible en franchise d'impôt, revenus/électricité/résultat de l'année, état des appareils avec ligne de total (hashrate et surconsommation de tous les appareils en minage, NAS compris si défini), derniers paiements, téléchargements |
| **Zuflüsse** (entrées) | Tous les paiements avec cours, source du cours et « Verursacht von » (part par ordinateur), tableau « Je Rechner » pour l'année ; autres entrées listées à part |
| **Strom** (électricité) | Heures de minage, watts moyens, kWh, ct/kWh moyens, coût par appareil et par mois, plus totaux pour tous les appareils (année et par mois) |
| **Auswertung** (analyse) | Période au choix (préréglages : dernière nuit, 24 h, 7/30 jours, mois, année) : par appareil, temps en minage/en pause/injoignable avec frise chronologique, hashrate moyen/max., hashes, kWh, coût, shares et XMR attribués ; valeur attendue (hashes ÷ difficulté × récompense de bloc) face aux paiements réels ; frise « Shares und Auszahlungen » avec « Verursacht von » ; par jour ; CSV |
| **Lose** (lots) | Lots FIFO avec coût d'acquisition et date **steuerfrei ab** (exonéré à partir du) |
| **Abgänge** (sorties) | Saisir/supprimer les transferts sortant du portefeuille de minage |
| **Verkaufs-Rechner** (calculateur de vente) | Simuler une vente/un échange prévu (rien n'est enregistré) |
| **Geräte** (appareils) | Appairer de nouveaux ordinateurs par code et les valider, modifier la surconsommation « à partir de maintenant » (historique), mettre hors service |

`/health` répond `ok` sans mot de passe (healthcheck Docker).

`/api/moneta` répond également sans mot de passe, mais uniquement avec le nom du service, la version, l'adresse
stratum et la possibilité d'appairage – c'est ainsi que les nouveaux ordinateurs trouvent le ledger dans le réseau
local. Sous `economics`, il renvoie aussi les valeurs pour le choix des threads lors de la mesure : difficulté et
récompense de bloc de votre propre nœud, dernier cours local (2 heures au plus) et tarif actuel, ainsi que le
rendement par H/s et le coût d'électricité par watt et par jour (`null` tant que la valeur du nœud ou le cours
manque). `/api/pair` (code d'appairage) et `/api/heartbeat` (jeton de l'appareil) n'acceptent que du JSON envoyé
par les ordinateurs, voir [Appairer des ordinateurs](#appairer-des-ordinateurs).

**Actualisation :** tant que l'onglet est ouvert, la vue d'ensemble récupère de nouvelles valeurs toutes les
30 s sans recharger la page (`/api/live`, JSON, même identification ; en pause dans un onglet en arrière-plan).
À côté de l'année, elle indique l'âge de la dernière récupération, ou « Verbindung verloren » (connexion perdue).
Sans JavaScript, la vue d'ensemble se recharge toutes les 2 minutes. Les données elles-mêmes sont collectées par
le ledger en arrière-plan : machines toutes les `poll_seconds` (60 s par défaut), portefeuille toutes les 120 s,
historique des cours toutes les 10 minutes.

## Appairer des ordinateurs

De nouveaux ordinateurs peuvent être ajoutés sans entrée dans `config.toml` :

1. Tableau de bord → **Geräte** → « Neuen Rechner koppeln – Code erzeugen ». Le code à 6 chiffres est valable
   10 minutes et une seule fois ; après cinq tentatives erronées, il devient invalide.
2. L'ordinateur s'inscrit avec le code via `POST /api/pair` : nom, URL de XMRig (adresses du réseau local
   uniquement), jeton d'API, profil de l'appareil (modèle, cœurs) et – s'il a été mesuré – une proposition de
   threads et de surconsommation. L'installateur et l'application de barre des menus s'en chargeront avec la
   prochaine mise à jour de `deploy/mac`.
3. L'ordinateur apparaît sous **Wartet auf Freigabe** (en attente de validation). Vérifiez ou saisissez la
   surconsommation et la note de mesure, puis **Freigeben** (valider). Ce n'est qu'à partir de là qu'il est
   interrogé ; la valeur est figée à chaque relevé, comme pour `[[miner]]`.
4. Si la surconsommation change (p. ex. autre nombre de threads), enregistrez une nouvelle valeur sous **Aktive
   Rechner** : elle s'applique à partir de l'enregistrement ; les relevés antérieurs restent inchangés. Le rapport
   Excel (feuille « Geräte ») affiche l'historique avec « gültig ab » (valable à partir du). **Stilllegen** (mettre
   hors service) arrête l'interrogation ; l'historique et le nom restent visibles.

Les ordinateurs appairés se signalent avec leur jeton via `POST /api/heartbeat` ; une IP modifiée est reprise.
Les ordinateurs de `[[miner]]` continuent de fonctionner sans changement (toute modification y nécessite
toujours un redémarrage du conteneur).

## Paiement → ordinateur

P2Pool paie selon PPLNS : un paiement se répartit sur toutes les shares de la fenêtre des 2160 derniers blocs de
la sidechain (mini ≈ 6 h, nano ≈ 18 h), pondérées par leur difficulté. Pour chaque paiement, le ledger indique donc
quels ordinateurs y ont participé et pour quelle part – sous **Zuflüsse** (« Verursacht von », tableau
« Je Rechner ») et sous **Auswertung** (frise « Shares und Auszahlungen », colonnes « Shares » et
« zugeordnet XMR »).

- **exakt** (exact) : à partir du journal P2Pool. Chaque share propre y figure avec heure, difficulté et adresse du
  client (`SHARE FOUND: … client <IP:port>[, user <nom>]`), chaque paiement avec la hauteur du bloc. Le ledger lit
  le journal en continu toutes les 60 s (tables `p2pool_shares`, `p2pool_payouts`). Le ledger reconnaît
  l'ordinateur d'une share à son login XMRig : l'installateur de `deploy/mac` configure XMRig
  avec le nom de l'appareil comme login (`-u <nom>`, enregistré dans `~/.config/moneta/name`, repris du ledger
  pour les ordinateurs appairés). Sinon, c'est l'IP du client issue de `[[miner]]` ou de l'appairage qui compte.
- **eindeutig** (univoque) : login `x` et une adresse qui n'appartient à aucun ordinateur – typique lorsque P2Pool,
  dans le réseau Docker, ne voit que l'adresse de la passerelle. Ce sont alors les temps de minage du ledger qui
  tranchent : si un seul ordinateur minait au moment de la share (± deux interrogations, à l'heure après 30 jours),
  elle lui revient. Le résultat est enregistré par share. Condition : tous les ordinateurs du pool sont connus du
  ledger.
- **teilweise** (partiel) : le journal ne commence qu'à l'intérieur de la fenêtre de ce paiement.
- **geschätzt** (estimé) : si plusieurs ordinateurs minaient au moment d'une share, elle est répartie selon leur
  hashrate à cet instant (losange creux dans le graphique). Sans share issue du journal (journal absent ou
  commençant plus tard), la répartition suit la part de hashes sur toute la fenêtre. Aucun ordinateur en minage
  selon le ledger : « unbekannt ».

**Activer :** le service `ledger` reçoit le volume P2Pool en lecture seule (`deploy/nas/compose.yaml`) :

```yaml
    volumes:
      - ./ledger/data:/data
      - p2pool-data:/p2pool:ro
```

Remplacer ensuite `compose.yaml` sur le NAS et lancer `sudo docker compose -p monero-pool up -d`. Sans ce volume,
tout fonctionne comme avant, seulement « geschätzt ». **Historique :** P2Pool ne fait pas lui-même la rotation de
son journal ; tant que `p2pool.log` n'a pas été supprimé, le ledger lit tout l'historique au premier démarrage et
attribue aussi exactement les paiements plus anciens.

Affichage uniquement : entrées, cours, rapport et traitement fiscal restent inchangés ; fiscalement, c'est toujours
le paiement entier qui compte. Aucun service externe comme p2pool.observer n'est interrogé, car cela relierait
l'adresse de minage à votre IP.

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
| `devices.py` | Ordinateurs appairés : code d'appairage, inscription, validation, historique des watts, heartbeat |
| `activity.py` | Valeurs horaires par appareil, analyse sur des périodes |
| `shares.py` | Lire le journal P2Pool, attribuer les paiements aux ordinateurs (affichage uniquement) |
| `network.py` | Difficulté et récompense de bloc depuis votre propre nœud |
| `ledger.py` | Lots, FIFO, délais, synthèse annuelle, calculateur de vente |
| `report.py` | Export Excel et CSV |
| `web.py` | Tableau de bord, formulaires, téléchargements, authentification, protection CSRF |
| `version.py` | Informations de version issues des arguments de build |

Tests : `python -m pytest -q ledger/tests` (faux portefeuille, faux XMRig, faux cours – pas besoin d'Internet).

## Limites

- Analyse : les valeurs à la minute (avec frise) sont conservées 30 jours, ensuite des valeurs horaires. Hashes =
  hashrate annoncé × intervalle d'interrogation (approximation) ; la valeur attendue ignore les uncles/orphelins.
  Affichage uniquement, pas une base fiscale.
- Paiement → ordinateur : la fenêtre est temporelle (2160 × temps de bloc) et n'est donc qu'une approximation de
  la fenêtre PPLNS ; les uncles sont ignorés. Derrière le proxy de ports de Docker, P2Pool ne voit que
  l'adresse de la passerelle ; c'est alors le login XMRig qui compte. Les shares antérieures sont attribuées via
  les temps de minage.
- CoinGecko (gratuit, sans garantie) ; via l'API gratuite, les cours historiques ne remontent qu'à environ un an.
- Le temps de minage n'est compté que tant que le ledger tourne et joint l'ordinateur (coûts plutôt sous-estimés
  que surestimés).
- Les frais de réseau ne sont pas déduits dans le calculateur de vente.
- Tableau de bord en HTTP : le mot de passe circule en clair dans le LAN (HTTPS via proxy inverse figure dans la
  [feuille de route](../../ROADMAP.md)).
- La logique fiscale applique les règles **allemandes** (voir [Méthodologie fiscale](tax-methodology.md)) ; des
  profils pour d'autres pays sont prévus dans la feuille de route.
- Appairage : le jeton et les informations de l'appareil circulent en clair dans le LAN, comme le mot de passe
  du tableau de bord. Sans code valide, aucun ordinateur ne peut s'inscrire, et sans validation aucun n'est
  enregistré.
