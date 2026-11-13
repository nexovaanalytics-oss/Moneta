#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
# Startet XMRig gegen den P2Pool auf der NAS – mit lesender API für den XMR-Ledger.
#
#   ./xmrig-start.sh        alle Kerne
#   ./xmrig-start.sh 3      3 Threads
#
# Einmalig anlegen (siehe docs/de/setup-mac.md; EN: docs/en/setup-mac.md):
#   ~/.config/moneta/pool          Adresse des P2Pool-Stratum, z. B. 192.168.1.10:3333
#   ~/.config/moneta/xmrig-token   API-Token für den XMR-Ledger (chmod 600)
set -euo pipefail

CONF_DIR="${CONF_DIR:-$HOME/.config/moneta}"
POOL="${POOL:-$( { [ -r "$CONF_DIR/pool" ] && tr -d '[:space:]' < "$CONF_DIR/pool"; } || true )}"
API_PORT="${API_PORT:-18000}"
TOKEN_FILE="${TOKEN_FILE:-$CONF_DIR/xmrig-token}"
THREADS="${1:-}"

if [ -z "$POOL" ]; then
  echo "Pool-Adresse fehlt: echo '<NAS-IP>:3333' > $CONF_DIR/pool  (oder POOL=… setzen)" >&2
  exit 1
fi

if [ ! -r "$TOKEN_FILE" ]; then
  echo "Token-Datei fehlt: $TOKEN_FILE" >&2
  echo "Anlegen:  mkdir -p ~/.config/moneta && openssl rand -hex 16 > $TOKEN_FILE && chmod 600 $TOKEN_FILE" >&2
  exit 1
fi
TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"

args=(-o "$POOL" --cpu-priority 0 --pause-on-battery
      --http-host 0.0.0.0 --http-port "$API_PORT" --http-access-token "$TOKEN")
if [ -n "$THREADS" ]; then
  args+=(-t "$THREADS")
fi

# caffeinate verhindert den Ruhezustand, solange XMRig läuft
exec caffeinate -is xmrig "${args[@]}"
