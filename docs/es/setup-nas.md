# Instalación en el NAS

🌐 [Deutsch](../de/setup-nas.md) · [English](../en/setup-nas.md) · [Français](../fr/setup-nas.md) · **Español**

Descrita con el ejemplo de un **Synology DS920+** (DSM 7.2, Container Manager, 8 GB de RAM). Funciona igual en
otros sistemas x86-64 con Docker Compose. Marcadores: `<IP-NAS>`, `<USUARIO-NAS>`.

Requisitos: IP fija para el NAS, SSH activado (DSM: Panel de control → Terminal y SNMP), ≥ 100 GB libres para la
blockchain podada.

## 1. Crear carpetas

```bash
ssh <USUARIO-NAS>@<IP-NAS>
sudo mkdir -p /volume1/docker/monero/ledger/data /volume1/docker/monero/ledger/wallets
cd /volume1/docker/monero
```

Copiar los archivos del repositorio (desde tu equipo, dentro de la carpeta del repositorio):

```bash
NAS=<USUARIO-NAS>@<IP-NAS>
ssh $NAS "cat > /volume1/docker/monero/compose.yaml" < deploy/nas/compose.yaml
ssh $NAS "cat > /volume1/docker/monero/ledger/data/config.example.toml" < ledger/config.example.toml
```

## 2. Crear `.env` (en el NAS)

```bash
cd /volume1/docker/monero
cat > .env <<'EOF'
XMR_ADDRESS=4...
LEDGER_IMAGE=ghcr.io/nexovaanalytics-oss/xmr-ledger
LEDGER_VERSION=1.1.0
EOF
chmod 600 .env
```

`XMR_ADDRESS` es la **dirección principal** de una billetera exclusiva para minar (95 caracteres, empieza por
`4`). No una subdirección (`8…`), ni una dirección integrada, ni una dirección de "XMR envuelto" de otra
blockchain.

## 3. `config.toml` para el ledger

Consulta [Ledger → Configuración](ledger.md#configuración). Coloca el archivo terminado en
`/volume1/docker/monero/ledger/data/config.toml`.

## 4. Arrancar

```bash
cd /volume1/docker/monero
sudo docker compose -p monero-pool pull
sudo docker compose -p monero-pool up -d
sudo docker ps --format "table {{.Names}}\t{{.Status}}"
```

Si el proyecto se gestiona en Container Manager de Synology, usa en `-p` exactamente su nombre de proyecto; si no,
Docker crea un segundo proyecto y falla por los nombres fijos de los contenedores. Si en la carpeta hay varios
archivos Compose (`compose.yaml` y `docker-compose.yml`), Docker usa `compose.yaml`; conserva solo uno.

## Notas sobre la configuración

- **monerod:** `--prune-blockchain --sync-pruned-blocks` (≈ 100 GiB en lugar de ≈ 250 GiB), RPC restringido en
  18089, ZMQ en 18084, lista de bloqueo DNS contra nodos espía. `--db-sync-mode=fast` solo con SAI.
- **p2pool:** `--mini` (para hashrates domésticos), `--light-mode` (ahorra ~2 GB de RAM que el sistema usa como
  caché de archivos para monerod). `--zmq-port 18084` debe coincidir con el `--zmq-pub` de monerod.
- **Primera sincronización** en disco duro con una CPU de gama básica: varios días. Progreso:
  `sudo docker logs --tail 5 monerod` (líneas "Synced …/…"). Hasta entonces P2Pool indica "unhealthy".
