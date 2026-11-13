# Setup NAS

🌐 **Deutsch** · [English](../en/setup-nas.md) · [Français](../fr/setup-nas.md) · [Español](../es/setup-nas.md)

Beschrieben am Beispiel einer **Synology DS920+** (DSM 7.2, Container Manager, 8 GB RAM). Auf anderen
x86-64-Systemen mit Docker Compose funktioniert es genauso. Platzhalter: `<NAS-IP>`, `<NAS-BENUTZER>`.

Voraussetzungen: feste IP der NAS, SSH aktiviert (DSM: Systemsteuerung → Terminal & SNMP),
≥ 100 GB frei für die pruned Blockchain.

## 1. Ordner anlegen

```bash
ssh <NAS-BENUTZER>@<NAS-IP>
sudo mkdir -p /volume1/docker/monero/ledger/data /volume1/docker/monero/ledger/wallets
cd /volume1/docker/monero
```

Dateien aus dem Repository übertragen (vom Rechner aus, im Repository-Ordner):

```bash
NAS=<NAS-BENUTZER>@<NAS-IP>
ssh $NAS "cat > /volume1/docker/monero/compose.yaml" < deploy/nas/compose.yaml
ssh $NAS "cat > /volume1/docker/monero/ledger/data/config.example.toml" < ledger/config.example.toml
```

## 2. `.env` anlegen (auf der NAS)

```bash
cd /volume1/docker/monero
cat > .env <<'EOF'
XMR_ADDRESS=4...
LEDGER_IMAGE=ghcr.io/nexovaanalytics-oss/xmr-ledger
LEDGER_VERSION=1.1.0
EOF
chmod 600 .env
```

`XMR_ADDRESS` ist die **Hauptadresse** einer eigenen Mining-Wallet (95 Zeichen, beginnt mit `4`). Keine
Subadresse (`8…`), keine integrierte Adresse, keine „Wrapped XMR“-Adresse einer anderen Blockchain.

## 3. `config.toml` für den Ledger

Siehe [Ledger → Konfiguration](ledger.md#konfiguration). Die fertige Datei nach
`/volume1/docker/monero/ledger/data/config.toml` legen.

## 4. Starten

```bash
cd /volume1/docker/monero
sudo docker compose -p monero-pool pull
sudo docker compose -p monero-pool up -d
sudo docker ps --format "table {{.Names}}\t{{.Status}}"
```

Wird das Projekt im Synology Container Manager geführt, als `-p` genau dessen Projektnamen verwenden –
sonst legt Docker ein zweites Projekt an und scheitert an den festen Container-Namen. Liegen im Ordner
mehrere Compose-Dateien (`compose.yaml` und `docker-compose.yml`), nimmt Docker `compose.yaml`; nur eine behalten.

## Hinweise zu den Einstellungen

- **monerod:** `--prune-blockchain --sync-pruned-blocks` (≈ 100 GiB statt ≈ 250 GiB), eingeschränkter RPC auf
  18089, ZMQ auf 18084, DNS-Blockliste gegen Spionage-Nodes. `--db-sync-mode=fast` nur mit USV.
- **p2pool:** `--mini` (für Heim-Hashraten), `--light-mode` (spart ~2 GB RAM, die das System als Datei-Cache
  für monerod nutzt). `--zmq-port 18084` muss zum `--zmq-pub` von monerod passen.
- **Erste Synchronisation** auf HDD mit einer Einsteiger-CPU: mehrere Tage. Fortschritt:
  `sudo docker logs --tail 5 monerod` (Zeilen „Synced …/…“). P2Pool meldet bis dahin „unhealthy“.
