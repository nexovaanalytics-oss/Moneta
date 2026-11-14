# Décisions de conception

🌐 [Deutsch](../de/design-decisions.md) · [English](../en/design-decisions.md) · **Français** · [Español](../es/design-decisions.md)

Pourquoi Moneta est construit ainsi. Ajouter les nouvelles entrées en haut (date, contexte, décision,
conséquences). La [version allemande](../de/design-decisions.md) sert de référence.

### D-10 · 14/11/2026 – Appairer de nouveaux ordinateurs par code, validation dans le tableau de bord
De nouveaux ordinateurs doivent pouvoir s'ajouter sans modification manuelle de `config.toml`. Le ledger sert de
point central : il répond sans mot de passe à `GET /api/moneta` (service, version, adresse stratum uniquement) afin
que l'installateur et l'application le trouvent dans le réseau local ; Bonjour/mDNS est écarté, car le conteneur
ne peut pas faire de multicast depuis le réseau bridge. L'appairage utilise un code à 6 chiffres issu du tableau de
bord (10 minutes, usage unique, invalide après cinq tentatives erronées) via `POST /api/pair`. Comme il ne s'agit
pas d'un formulaire de navigateur, le code, un corps uniquement JSON et une limite de taille y remplacent la
vérification same-origin ; `/api/heartbeat` vérifie le jeton de l'appareil. Un ordinateur appairé n'est interrogé
qu'après validation avec une surconsommation mesurée – sinon n'importe quel appareil du LAN pourrait inscrire des
coûts d'électricité dans les données fiscalement pertinentes. Les watts sont stockés sous forme d'historique avec
`valid_from` et jamais écrasés ; `[[miner]]` dans `config.toml` reste possible.

### D-09 · 13/11/2026 – Démarrage du mineur via une application de barre des menus, compilée localement plutôt que distribuée signée
Les ordinateurs doivent pouvoir être configurés sans connaissance du terminal et démarrés d'un clic. Un
installateur (`deploy/mac/install.sh`) configure XMRig comme agent launchd et compile l'application de barre des
menus à partir du code source sur l'ordinateur lui-même (`swiftc` des Command Line Tools, dont Homebrew a de toute
façon besoin). Les programmes compilés localement ne portent pas d'attribut de quarantaine ; Gatekeeper ne pose donc
pas de question, et ni compte développeur Apple payant ni notarisation ne sont nécessaires. XMRig n'est pas fourni
mais installé via Homebrew (mises à jour propres) ; l'application ne fait que piloter l'agent et lire
l'API locale de XMRig. L'entrée `[[miner]]` dans `config.toml` reste volontairement une étape manuelle : les watts
sont figés à chaque relevé et doivent être mesurés au préalable. Une application signée et notarisée à télécharger
reste une option pour plus tard.

### D-08 · 13/11/2026 – Multilingue et ouvert aux contributions
Moneta doit être utilisable au-delà des pays germanophones et inviter à participer. La langue du projet pour les
fichiers communautaires (README, CONTRIBUTING, CHANGELOG, SECURITY, modèles) est l'anglais ; le README, le guide
de contribution et le code de conduite existent aussi en allemand, français et espagnol. La documentation se
trouve dans `docs/<de|en|fr|es>/` avec des noms de fichiers identiques ; en cas de divergence, la version
allemande prévaut – en particulier pour la méthodologie fiscale, qui décrit le droit allemand. Le tableau de bord
et le rapport Excel restent en allemand pour l'instant ; leur traduction est en tête de la
[feuille de route](../../ROADMAP.md). Code de conduite : Contributor Covenant 3.0.

### D-07 · 13/11/2026 – Publication sous EUPL-1.2
Un copyleft qui couvre aussi l'exploitation en tant que service web ; versions officielles dans toutes les
langues de l'UE ; responsabilité et droit applicable selon le droit de l'UE. Licences tierces dans
[`THIRD_PARTY.md`](../../THIRD_PARTY.md), licence de Monero incluse dans l'image.

### D-06 · 13/11/2026 – Image construite par GitHub Actions, version fixée délibérément sur le serveur
GitHub Actions teste et construit `ghcr.io/nexovaanalytics-oss/xmr-ledger`. Sur le serveur, la version est fixée
dans `.env` (`LEDGER_VERSION`), sans mise à jour automatique. Chaque rapport Excel indique la version qui l'a
produit.

### D-05 · 13/11/2026 – Cours attribués localement depuis un historique à 5 minutes
Des requêtes du type « cours au moment X » révéleraient les heures de paiement au fournisseur de cours ; combinées
à l'adresse P2Pool publique, l'adresse IP pourrait être rattachée à l'adresse de minage. C'est pourquoi les
dernières 24 h sont chargées à intervalle fixe (actuellement toutes les 10 minutes) et stockées localement ; l'attribution se fait localement
(écart max. 15 min). Le cours du jour ne sert que de repli – seule la date est alors transmise.

### D-04 · 11/11/2026 – Coût de l'électricité = surconsommation mesurée × temps de minage enregistré
Sur un portable, une prise wattmètre mesure aussi la recharge et l'usage normal. La surconsommation est donc
mesurée une fois (charge − repos, +10 % pour l'alimentation) et la durée de fonctionnement est enregistrée
automatiquement via l'API XMRig. Les watts et le tarif sont figés à chaque enregistrement ; les modifications de
configuration n'ont d'effet que pour l'avenir.

### D-03 · 11/11/2026 – Portefeuille en lecture seule, sorties saisies à la main
La clé de dépense ne doit pas se trouver sur le serveur. `monero-wallet-rpc` fonctionne avec l'adresse + la clé
de visualisation. Un tel portefeuille voit les entrées mais pas les sorties : seules les entrées coinbase comptent
comme entrées de minage, les autres entrées (p. ex. la monnaie rendue) sont listées à part, les sorties sont
saisies dans le tableau de bord.

### D-02 · 11/11/2026 – Un lot par paiement, FIFO
Chaque paiement est une acquisition (coût d'acquisition = valeur à la réception) ; ordre de sortie FIFO ;
« exonéré à partir du » = le jour suivant l'expiration du délai d'un an (§§ 187, al. 1, 188, al. 2 BGB).
Détails : [Méthodologie fiscale](tax-methodology.md).

### D-01 · 11/11/2026 – Nœud et P2Pool sur le NAS, les ordinateurs ne font que calculer
Le nœud et le pool ont besoin de stockage mais presque pas de puissance de calcul – et le NAS tourne de toute
façon. monerod élagué avec `--sync-pruned-blocks`, P2Pool mini avec `--light-mode`. Les ordinateurs se connectent
uniquement via Stratum ; autant d'ordinateurs supplémentaires que l'on veut peuvent participer.
