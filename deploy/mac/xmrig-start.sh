#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
# Startet XMRig gegen den P2Pool auf der NAS – mit lesender API für den XMR-Ledger.
#
#   ./xmrig-start.sh        Threads aus ~/.config/moneta/threads, sonst alle Kerne
#   ./xmrig-start.sh 3      3 Threads
#
# Einmalig anlegen (deploy/mac/install.sh erledigt das; siehe docs/de/setup-mac.md, EN: docs/en/setup-mac.md):
#   ~/.config/moneta/pool          Adresse des P2Pool-Stratum, z. B. 192.168.1.10:3333
#   ~/.config/moneta/xmrig-token   API-Token für den XMR-Ledger (chmod 600)
#   ~/.config/moneta/threads       optional: Thread-Zahl oder "all"
#   ~/.config/moneta/name          optional: Gerätename im Ledger; XMRig meldet sich damit bei P2Pool an
#
# Wird auch vom launchd-Agent des Installers aufgerufen (Ausgabe dann im Log, ohne Farben).
set -euo pipefail

CONF_DIR="${CONF_DIR:-$HOME/.config/moneta}"
POOL="${POOL:-$( { [ -r "$CONF_DIR/pool" ] && tr -d '[:space:]' < "$CONF_DIR/pool"; } || true )}"
API_PORT="${API_PORT:-18000}"
TOKEN_FILE="${TOKEN_FILE:-$CONF_DIR/xmrig-token}"
THREADS="${1:-$( { [ -r "$CONF_DIR/threads" ] && tr -d '[:space:]' < "$CONF_DIR/threads"; } || true )}"
WORKER="${WORKER:-$( { [ -r "$CONF_DIR/name" ] && head -n 1 "$CONF_DIR/name"; } || true )}"

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

# launchd kennt /opt/homebrew/bin nicht von selbst – XMRig auch an den üblichen Homebrew-Orten suchen
XMRIG="${XMRIG:-$(command -v xmrig || true)}"
for candidate in /opt/homebrew/bin/xmrig /usr/local/bin/xmrig; do
  [ -n "$XMRIG" ] && break
  [ -x "$candidate" ] && XMRIG="$candidate"
done
if [ -z "$XMRIG" ]; then
  echo "xmrig nicht gefunden – installieren mit: brew install xmrig" >&2
  exit 1
fi

args=(-o "$POOL" --cpu-priority 0 --pause-on-battery
      --http-host 0.0.0.0 --http-port "$API_PORT" --http-access-token "$TOKEN")
case "$THREADS" in
  ""|all) ;;
  *[!0-9]*) echo "Ungültige Thread-Zahl: $THREADS" >&2; exit 1 ;;
  *) args+=(-t "$THREADS") ;;
esac
# Login = Gerätename: P2Pool schreibt ihn als „user“ zu jeder gefundenen Share ins Log. Daran ordnet der
# XMR-Ledger Shares und Auszahlungen diesem Rechner zu – auch wenn P2Pool hinter Docker nur eine interne Adresse
# sieht. P2Pool nutzt den Login nur dafür (ausgezahlt wird an die Adresse des Pools).
if [ -n "$WORKER" ]; then
  args+=(-u "$WORKER")
fi
if [ ! -t 1 ]; then
  args+=(--no-color)   # Ausgabe geht in ein Log
fi

# caffeinate verhindert den Ruhezustand, solange XMRig läuft. Es beobachtet diese PID, die nach dem exec
# XMRig gehört: Stoppt launchd (oder Ctrl-C) XMRig, endet caffeinate von selbst.
if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -is -w $$ &
fi
exec "$XMRIG" "${args[@]}"
