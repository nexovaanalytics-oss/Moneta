# NAS setup

🌐 [Deutsch](../de/setup-nas.md) · **English** · [Français](../fr/setup-nas.md) · [Español](../es/setup-nas.md)

Described using a **Synology DS920+** (DSM 7.2, Container Manager, 8 GB RAM) as the example. It works the same
on other x86-64 systems with Docker Compose. Placeholders: `<NAS-IP>`, `<NAS-USER>`.

Prerequisites: a fixed IP address for the NAS, SSH enabled (DSM: Control Panel → Terminal & SNMP),
≥ 100 GB free for the pruned blockchain.

## 1. Create folders

```bash
ssh <NAS-USER>@<NAS-IP>
sudo mkdir -p /volume1/docker/monero/ledger/data /volume1/docker/monero/ledger/wallets
cd /volume1/docker/monero
```

Copy the files from the repository (from your computer, inside the repository folder):

```bash
NAS=<NAS-USER>@<NAS-IP>
ssh $NAS "cat > /volume1/docker/monero/compose.yaml" < deploy/nas/compose.yaml
ssh $NAS "cat > /volume1/docker/monero/ledger/data/config.example.toml" < ledger/config.example.toml
```

## 2. Create `.env` (on the NAS)

```bash
cd /volume1/docker/monero
cat > .env <<'EOF'
XMR_ADDRESS=4...
LEDGER_IMAGE=ghcr.io/nexovaanalytics-oss/xmr-ledger
LEDGER_VERSION=1.1.0
EOF
chmod 600 .env
```

`XMR_ADDRESS` is the **primary address** of a dedicated mining wallet (95 characters, starts with `4`). Not a
subaddress (`8…`), not an integrated address, and not a "wrapped XMR" address on another blockchain.

## 3. `config.toml` for the ledger

See [Ledger → Configuration](ledger.md#configuration). Place the finished file at
`/volume1/docker/monero/ledger/data/config.toml`.

## 4. Start

```bash
cd /volume1/docker/monero
sudo docker compose -p monero-pool pull
sudo docker compose -p monero-pool up -d
sudo docker ps --format "table {{.Names}}\t{{.Status}}"
```

If the project is managed in Synology Container Manager, pass exactly its project name to `-p` – otherwise
Docker creates a second project and fails on the fixed container names. If the folder contains several Compose
files (`compose.yaml` and `docker-compose.yml`), Docker uses `compose.yaml`; keep only one.

## Notes on the settings

- **monerod:** `--prune-blockchain --sync-pruned-blocks` (≈ 100 GiB instead of ≈ 250 GiB), restricted RPC on
  18089, ZMQ on 18084, DNS blocklist against spy nodes. Use `--db-sync-mode=fast` only with a UPS.
- **p2pool:** `--mini` (for home hashrates), `--light-mode` (saves ~2 GB RAM, which the system then uses as file
  cache for monerod). `--zmq-port 18084` must match monerod's `--zmq-pub`.
- **Initial sync** on an HDD with an entry-level CPU: several days. Progress:
  `sudo docker logs --tail 5 monerod` (lines "Synced …/…"). Until then P2Pool reports "unhealthy".
