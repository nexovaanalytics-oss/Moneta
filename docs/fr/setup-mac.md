# Installation sur l'ordinateur (macOS)

🌐 [Deutsch](../de/setup-mac.md) · [English](../en/setup-mac.md) · **Français** · [Español](../es/setup-mac.md)

Rédigé pour macOS sur Apple Silicon ; sous Linux, les étapes sont analogues (XMRig via le gestionnaire de paquets
ou xmrig.com, mesure de la consommation p. ex. avec une prise wattmètre).

## Installation rapide : installateur et application de barre des menus

L'installateur couvre les étapes 1, 2 et 4 et configure XMRig comme agent launchd avec l'application de barre
des menus **Moneta Miner** (macOS 13 ou plus récent). Il peut être relancé sans risque (p. ex. après
`git pull`) ; les réglages existants sont conservés.

```bash
git clone https://github.com/nexovaanalytics-oss/Moneta.git ~/Moneta
~/Moneta/deploy/mac/install.sh
```

Ce que fait l'installateur :
- installe Homebrew et XMRig si nécessaire (build Homebrew ; comme tous les builds officiels, il reverse au moins
  1 % aux développeurs de XMRig, `--donate-level 0` est ignoré) ;
- **cherche le XMR-Ledger dans le réseau local** (toutes les adresses de votre réseau /24 sur le port 8090,
  `GET /api/moneta`) et en reprend l'adresse du pool. S'il n'en trouve aucun, il demande l'adresse du pool comme
  avant (ou indiquez `LEDGER=http://<IP-NAS>:8090`) ;
- crée le jeton d'API – ou reprend un jeton déjà présent dans `config.toml` pour cet ordinateur ;
- **propose le nombre de threads** : d'après la table de profils [`deploy/mac/profile.tsv`](../../deploy/mac/profile.tsv)
  (appareils mesurés) ou selon la règle empirique – sans ventilateur (MacBook Air) : cœurs performance − 1, avec
  ventilateur : tous les cœurs. Sur demande, il effectue directement la mesure (voir section 3) ;
- copie les scripts dans `~/Library/Application Support/Moneta/` et crée l'agent launchd `moneta.xmrig`
  (journal `~/Library/Logs/Moneta/xmrig.log`, redémarrage après un plantage, démarrage à l'ouverture de session
  au choix) ;
- compile l'application de barre des menus avec `swiftc` des Command Line Tools dans
  `~/Applications/Moneta Miner.app` et la lance à l'ouverture de session. Comme elle est compilée sur
  l'ordinateur lui-même, elle ne nécessite ni compte développeur Apple ni exception Gatekeeper ;
- si le pare-feu de macOS est actif, autorise les connexions entrantes pour `xmrig` (deux commandes `sudo`,
  après confirmation). Relancez l'installateur après `brew upgrade xmrig` – la règle dépend du chemin du
  programme ;
- **appaire l'ordinateur avec le ledger** : créez un code d'appairage dans le tableau de bord sous **Geräte** et
  saisissez-le dans l'installateur. L'ordinateur transmet son nom, son adresse, son jeton, son profil et – s'il a
  été mesuré – les threads et la surconsommation. Sans ledger ni code, il affiche comme avant un bloc
  `[[miner]]` (`~/.config/moneta/ledger-miner.toml`).

Ensuite : dans le tableau de bord sous **Geräte**, **validez** l'ordinateur avec la surconsommation mesurée
(préremplie à partir de la mesure) et cliquez sur **Miner starten** dans la barre des menus. Le ledger n'enregistre
l'ordinateur qu'à partir de la validation ; les watts sont figés à chaque relevé. Une IP fixe dans le routeur
reste recommandée, mais n'est plus indispensable : à chaque démarrage, l'ordinateur se signale au ledger
(`moneta-miner.sh heartbeat`) et une IP modifiée est reprise.

XMRig se connecte à P2Pool avec le nom de l'appareil (`~/.config/moneta/name`, repris du ledger pour les
ordinateurs appairés). Le ledger s'en sert pour attribuer shares et paiements à l'ordinateur, même si P2Pool ne
voit qu'une adresse interne dans le réseau Docker ([Paiement → ordinateur](ledger.md#paiement--ordinateur)).
Ordinateurs déjà configurés : `git pull` puis relancer `install.sh`.

Sans questions (p. ex. pour plusieurs ordinateurs) : `LEDGER=http://<IP-NAS>:8090 CODE=<code> THREADS=3 MEASURE=n
AUTOSTART=n FIREWALL=j START=n ~/Moneta/deploy/mac/install.sh`. Désinstaller : `~/Moneta/deploy/mac/install.sh
--uninstall` (réglages, journal et XMRig sont conservés).

## 1. Installer XMRig

```bash
# Homebrew, si `brew` est absent
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

brew install xmrig          # build Homebrew ; DONATE 1 % (minimum en amont)
```

## 2. Adresse du pool et jeton d'API

```bash
ipconfig getifaddr en0                      # IP de cet ordinateur – à réserver dans le routeur
mkdir -p ~/.config/moneta
echo '<IP-NAS>:3333' > ~/.config/moneta/pool
openssl rand -hex 16 > ~/.config/moneta/xmrig-token
chmod 600 ~/.config/moneta/xmrig-token
cat ~/.config/moneta/xmrig-token            # à reporter comme token dans le config.toml du ledger
```

## 3. Mesurer le hashrate et la surconsommation

**Automatiquement :** `deploy/mac/einmessen.sh` (proposé par l'installateur, ensuite aussi dans
`~/Library/Application Support/Moneta/einmessen.sh`) mesure la consommation au repos puis, par paliers jusqu'à
tous les cœurs, le hashrate et la puissance – sans ventilateur : cœurs performance − 1, tous les cœurs
performance, plus la moitié des cœurs efficacité et tous les cœurs (M4 à 4 + 6 cœurs : 3, 4, 7, 10) ; avec
ventilateur : cœurs performance, moitié des cœurs efficacité et tous. Les paliers sont mesurés dans l'ordre
croissant après une phase de chauffe (5 min sans ventilateur, pour saisir le bridage). Surconsommation =
(charge − repos) × 1,1, arrondie vers le haut, avec une note prête à l'emploi.

La proposition est le palier au meilleur solde entre rendement calculé et coût d'électricité par jour : rendement =
hashrate × 86 400 ÷ difficulté × récompense de bloc × cours, électricité = surconsommation × 24 h × tarif. Les
valeurs viennent de votre propre ledger (difficulté du nœud, cours local, tarif de `config.toml`) ; un palier
supplémentaire n'est rentable que si son rendement supplémentaire dépasse l'électricité supplémentaire. Sans
valeurs du ledger, c'est le meilleur hashrate par watt qui compte. Le tableau montre tous les paliers et
l'installateur permet d'en choisir n'importe lequel. Ce calcul oriente le choix des threads ; ce n'est pas une
grandeur fiscale.

Durée ≈ 10 min avec ventilateur, ≈ 30 min sans ; brancher l'alimentation, ne pas utiliser le Mac pendant ce temps,
`sudo` pour `powermetrics`. Vos propres paliers : `einmessen.sh 3 4 6`. La mesure mine déjà via P2Pool.
L'appairage transmet le résultat (`~/.config/moneta/einmessung.json`) comme proposition.

**À la main :**

Onglet 1 – générer la charge (sans pool), avec le nombre de threads prévu ensuite :

```bash
xmrig --bench=10M          # tous les cœurs
xmrig --bench=10M -t 3     # p. ex. 3 threads
```

Onglet 2 – mesurer après ~1 minute, puis arrêter XMRig et mesurer à nouveau au repos :

```bash
deploy/mac/strom-messen.sh
```

Surconsommation = charge − repos, **+10 %** de pertes de l'alimentation, arrondie légèrement vers le haut pour la
RAM (que `powermetrics` ne mesure pas). Reportez le résultat comme `watts`, et la date et la méthode comme `note`,
dans `config.toml`. Mesurez à nouveau si vous changez le nombre de threads (effet à partir de ce moment).

### Ordres de grandeur

Le hashrate et la surconsommation dépendent de la puce, du refroidissement et du nombre de threads. Règles
empiriques : les Mac avec ventilateur tournent sur tous les cœurs sans bridage notable. Les Mac sans ventilateur
(MacBook Air) sont bridés sous charge continue après quelques minutes ; cœurs performance − 1 y donne
généralement le meilleur hashrate par watt. `einmessen.sh` mesure les valeurs de votre appareil ; les
recommandations de threads par puce figurent dans [`deploy/mac/profile.tsv`](../../deploy/mac/profile.tsv).

Vous avez des mesures pour un autre appareil ? Partagez-les via une issue (« Device measurement ») – voir
[CONTRIBUTING](../../CONTRIBUTING.fr.md).

## 4. Miner

Seulement une fois le nœud synchronisé et P2Pool « healthy » :

Avec l'installateur : barre des menus → **Moneta Miner** → *Miner starten* / *Miner stoppen* (démarrer /
arrêter) ; on y trouve aussi les threads, le démarrage à l'ouverture de session, le journal et un accès direct au
tableau de bord. La fenêtre de l'application montre le fonctionnement de ce Mac :

- le hashrate actuel à côté de l'icône dans la barre des menus (désactivable),
- l'historique des 15 dernières minutes / 1 h / 6 h avec une frise *en cours / en pause / arrêté*, le hashrate
  moyen et le temps de pause (en mémoire de l'application uniquement ; l'historique sur plusieurs jours est dans
  le tableau de bord),
- le hashrate par thread (par ex. pour repérer des cœurs d'efficacité plus lents), le ping du pool et les shares
  stratum acceptées/rejetées (pas les shares de la sidechain P2Pool),
- la source d'alimentation, le niveau de batterie et l'état thermique – et, en cas de pause, la **raison** :
  XMRig tourne avec `--pause-on-battery` et se met en pause dès que macOS passe sur batterie. Cela arrive aussi
  adaptateur branché lorsqu'un limiteur de charge comme AlDente laisse la batterie se décharger jusqu'à sa limite
  basse ; l'application détecte les limiteurs de charge actifs et un adaptateur branché et l'indique. Elle signale
  aussi le mode économie d'énergie et le bridage thermique.

Le bouton *Dashboard* ouvre `http://<hôte-du-pool>:8090` ; indiquer une autre adresse dans
`~/.config/moneta/dashboard`. Mise à jour : `git pull`, puis relancer `deploy/mac/install.sh` (les réglages sont
conservés).

La même chose dans le terminal :

```bash
MM="$HOME/Library/Application Support/Moneta/moneta-miner.sh"
"$MM" start                  # ou stop, restart
"$MM" status
"$MM" threads 3              # ou : all – redémarre XMRig s'il tourne
"$MM" autostart on           # ou : off
"$MM" log -f
```

Sans l'installateur, à la main au premier plan :

```bash
deploy/mac/xmrig-start.sh        # threads de ~/.config/moneta/threads, sinon tous les cœurs
deploy/mac/xmrig-start.sh 3      # 3 threads
```

Au premier démarrage, macOS demande d'autoriser les connexions entrantes pour `xmrig` → **Autoriser** (API XMRig
pour le ledger). Test depuis le NAS :

```bash
curl -s -H "Authorization: Bearer <token>" http://<IP-ORDINATEUR>:18000/2/summary | head -c 200
```

Remarques :
- Uniquement sur secteur (`--pause-on-battery`) ; pour les portables, limite de charge à ~80 % (p. ex. AlDente) et
  surface dure.
- `MEMORY 98 %` dans la sortie de XMRig correspond au cache de macOS ; ce qui compte est la pression mémoire dans
  le Moniteur d'activité.
- « huge pages unavailable » est normal sous macOS.
- Windows : Smart App Control bloque XMRig sans possibilité d'exception ; envisagez WSL2.

## 5. Portefeuille de minage

```bash
brew install monero
mkdir -p ~/Monero/wallet
monero-wallet-cli --offline --generate-new-wallet ~/Monero/wallet/mining
```

- Notez les mots de la phrase de récupération sur papier (langue anglaise pour une compatibilité maximale) ; ne
  les stockez jamais sous forme numérique.
- `set setup-background-mining 0` – sinon le portefeuille ferait miner le nœud en solo.
- `address` affiche l'adresse principale (`4…`) pour `.env` ; `viewkey` affiche la clé de visualisation (secret)
  pour le ledger.

Solde et transferts via votre propre nœud :

```bash
monero-wallet-cli --wallet-file ~/Monero/wallet/mining --daemon-address <IP-NAS>:18089 --trusted-daemon
```

Commandes utiles : `refresh`, `balance`, `show_transfers`, `transfer <adresse> <montant>`,
`sweep_all <adresse>`, `export_transfers in output=<fichier.csv>`. Les XMR minés sont bloqués ~2 heures
(60 blocs). Enregistrez ensuite chaque transfert dans le ledger sous **Abgänge** (sorties).
