# Installation sur le NAS

🌐 [Deutsch](../de/setup-nas.md) · [English](../en/setup-nas.md) · **Français** · [Español](../es/setup-nas.md)

Décrite avec l'exemple d'un **Synology DS920+** (DSM 7.2, Container Manager, 8 Go de RAM). Cela fonctionne de la
même manière sur d'autres systèmes x86-64 avec Docker Compose. Paramètres à remplacer : `<IP-NAS>`,
`<UTILISATEUR-NAS>`.

Prérequis : une adresse IP fixe pour le NAS, SSH activé (DSM : Panneau de configuration → Terminal & SNMP),
≥ 100 Go libres pour la blockchain élaguée.

## 1. Créer les dossiers

```bash
ssh <UTILISATEUR-NAS>@<IP-NAS>
sudo mkdir -p /volume1/docker/monero/ledger/data /volume1/docker/monero/ledger/wallets
cd /volume1/docker/monero
```

Copier les fichiers du dépôt (depuis votre ordinateur, dans le dossier du dépôt) :

```bash
NAS=<UTILISATEUR-NAS>@<IP-NAS>
ssh $NAS "cat > /volume1/docker/monero/compose.yaml" < deploy/nas/compose.yaml
ssh $NAS "cat > /volume1/docker/monero/ledger/data/config.example.toml" < ledger/config.example.toml
```

## 2. Créer `.env` (sur le NAS)

```bash
cd /volume1/docker/monero
cat > .env <<'EOF'
XMR_ADDRESS=4...
LEDGER_IMAGE=ghcr.io/nexovaanalytics-oss/xmr-ledger
LEDGER_VERSION=1.1.0
EOF
chmod 600 .env
```

`XMR_ADDRESS` est l'**adresse principale** d'un portefeuille dédié au minage (95 caractères, commence par `4`).
Pas de sous-adresse (`8…`), pas d'adresse intégrée, pas d'adresse « XMR wrappé » d'une autre blockchain.

## 3. `config.toml` pour le ledger

Voir [Ledger → Configuration](ledger.md#configuration). Placez le fichier terminé dans
`/volume1/docker/monero/ledger/data/config.toml`.

## 4. Démarrer

```bash
cd /volume1/docker/monero
sudo docker compose -p monero-pool pull
sudo docker compose -p monero-pool up -d
sudo docker ps --format "table {{.Names}}\t{{.Status}}"
```

Si le projet est géré dans le Container Manager de Synology, passez exactement son nom de projet à `-p` – sinon
Docker crée un second projet et échoue à cause des noms de conteneurs fixes. Si le dossier contient plusieurs
fichiers Compose (`compose.yaml` et `docker-compose.yml`), Docker utilise `compose.yaml` ; n'en gardez qu'un.

## Remarques sur les paramètres

- **monerod :** `--prune-blockchain --sync-pruned-blocks` (≈ 100 Gio au lieu de ≈ 250 Gio), RPC restreint sur
  18089, ZMQ sur 18084, liste de blocage DNS contre les nœuds espions. `--db-sync-mode=fast` uniquement avec
  un onduleur.
- **p2pool :** `--mini` (pour les hashrates domestiques), `--light-mode` (économise ~2 Go de RAM, que le système
  utilise alors comme cache de fichiers pour monerod). `--zmq-port 18084` doit correspondre au `--zmq-pub` de
  monerod.
- **Première synchronisation** sur disque dur avec un processeur d'entrée de gamme : plusieurs jours.
  Progression : `sudo docker logs --tail 5 monerod` (lignes « Synced …/… »). D'ici là, P2Pool indique
  « unhealthy ».
