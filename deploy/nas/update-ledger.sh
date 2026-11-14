#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
# Spielt eine neue Version des XMR-Ledgers auf der NAS ein – im Ordner mit compose.yaml und .env.
#
#   sudo bash update-ledger.sh             neueste Ledger-Version von GitHub vorschlagen und nach Rückfrage einspielen
#   sudo bash update-ledger.sh 1.2.0       genau diese Version einspielen
#   sudo bash update-ledger.sh --check     nur anzeigen: eingetragene und neueste Version, nichts ändern
#   -y                                     ohne Rückfrage
#
# Ablauf: Image ziehen (vorher wird nichts geändert) → Datenbank sichern (SQLite-Backup im laufenden
# Container, also inkl. WAL) → LEDGER_VERSION in .env setzen → wallet-rpc und ledger neu starten → Log zeigen.
# Die Version bleibt fest in .env eingetragen; das Skript aktualisiert nichts von selbst.
#
# Umgebungsvariablen: MONETA_DIR (Standard: aktueller Ordner), COMPOSE_PROJECT (Standard: monero-pool),
# MONETA_REPO (Standard: nexovaanalytics-oss/Moneta, für Forks).
set -euo pipefail

DIR="${MONETA_DIR:-$PWD}"
PROJECT="${COMPOSE_PROJECT:-monero-pool}"
REPO="${MONETA_REPO:-nexovaanalytics-oss/Moneta}"
SERVICES=(wallet-rpc ledger)

die() { echo "Fehler: $*" >&2; exit 1; }

usage() { sed -n '3,9s/^# \{0,1\}//p' "$0"; }

check_only=0
assume_yes=0
target=""
for arg in "$@"; do
  case "$arg" in
    --check) check_only=1 ;;
    -y|--yes) assume_yes=1 ;;
    -h|--help) usage; exit 0 ;;
    -*) die "unbekannte Option: $arg (Hilfe: --help)" ;;
    *) [ -z "$target" ] || die "nur eine Version angeben"; target="${arg#ledger-v}"; target="${target#v}" ;;
  esac
done

valid_version() { [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; }

# Vergleicht zwei Versionen X.Y.Z; Ausgabe -1, 0 oder 1.
version_cmp() {
  local i a b
  IFS=. read -r -a a <<< "$1"
  IFS=. read -r -a b <<< "$2"
  for i in 0 1 2; do
    if (( a[i] < b[i] )); then echo -1; return; fi
    if (( a[i] > b[i] )); then echo 1; return; fi
  done
  echo 0
}

# Neueste veröffentlichte Ledger-Version (Tag ledger-vX.Y.Z, keine Entwürfe/Vorabversionen ohne X.Y.Z-Form).
latest_version() {
  local json
  json=$(curl -fsSL --max-time 20 -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO/releases?per_page=30") \
    || die "GitHub nicht erreichbar (https://api.github.com/repos/$REPO/releases)"
  printf '%s\n' "$json" \
    | grep -o '"tag_name"[[:space:]]*:[[:space:]]*"ledger-v[0-9]*\.[0-9]*\.[0-9]*"' \
    | grep -o '[0-9]*\.[0-9]*\.[0-9]*' \
    | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1
}

cd "$DIR" || die "Ordner $DIR nicht gefunden"
[ -f compose.yaml ] || [ -f docker-compose.yml ] || die "keine compose.yaml in $DIR – im NAS-Ordner des Stacks starten oder MONETA_DIR setzen"
[ -f .env ] || die "keine .env in $DIR"
[ -r .env ] || die "$DIR/.env nicht lesbar – mit sudo starten"
current=$(sed -n 's/^LEDGER_VERSION=//p' .env | tail -n 1 | tr -d "\"' \r")
[ -n "$current" ] || die "LEDGER_VERSION fehlt in $DIR/.env"

if [ -z "$target" ]; then
  target=$(latest_version)
  [ -n "$target" ] || die "keine Ledger-Version (ledger-vX.Y.Z) unter github.com/$REPO/releases gefunden"
  source_note="neueste Version auf GitHub"
else
  source_note="angegeben"
fi
valid_version "$target" || die "ungültige Version: $target (erwartet X.Y.Z)"

echo "Ordner:       $DIR (Projekt $PROJECT)"
echo "Eingetragen:  $current"
echo "Ziel:         $target ($source_note)"
echo "Änderungen:   https://github.com/$REPO/releases/tag/ledger-v$target"

if [ "$check_only" = 1 ]; then
  if valid_version "$current" && [ "$(version_cmp "$current" "$target")" -lt 0 ]; then
    echo "→ Update verfügbar: sudo bash $0 $target"
  else
    echo "→ Kein Update nötig."
  fi
  exit 0
fi

[ "$(id -u)" = 0 ] || die "bitte mit sudo starten: sudo bash $0 ${*:-}"
command -v docker >/dev/null || die "docker nicht gefunden"

if [ "$current" = "$target" ]; then
  echo "→ Version $target ist bereits eingetragen – nichts zu tun."
  exit 0
fi
if valid_version "$current" && [ "$(version_cmp "$current" "$target")" -gt 0 ]; then
  echo
  echo "Achtung: $target ist älter als $current. Datenbank-Migrationen gehen nur vorwärts – eine ältere"
  echo "Version kann mit dem neueren Schema scheitern. Zurück nur zusammen mit der passenden Sicherung."
fi

if [ "$assume_yes" != 1 ]; then
  echo
  read -r -p "Ledger von $current auf $target umstellen? [j/N] " answer
  case "$answer" in j|J|ja|Ja|y|Y) ;; *) echo "Abgebrochen, nichts geändert."; exit 1 ;; esac
fi

echo
echo "1/4 Image $target ziehen …"
LEDGER_VERSION="$target" docker compose -p "$PROJECT" pull "${SERVICES[@]}" \
  || die "Image $target nicht verfügbar (Release-Workflow fertig?) – nichts geändert"

echo "2/4 Datenbank sichern …"
container=$(docker compose -p "$PROJECT" ps -q ledger 2>/dev/null || true)
backup="ledger-vor-$target-$(date +%Y%m%d-%H%M%S).sqlite"
if [ -n "$container" ] && [ "$(docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null)" = true ]; then
  docker exec "$container" python -c \
    "import sqlite3; sqlite3.connect('/data/ledger.sqlite').backup(sqlite3.connect('/data/$backup'))" \
    || die "Sicherung fehlgeschlagen – nichts geändert"
  echo "    ledger/data/$backup"
else
  die "Ledger-Container läuft nicht – Sicherung im laufenden Container nicht möglich. Zuerst starten:
  sudo docker compose -p $PROJECT up -d ledger"
fi

echo "3/4 LEDGER_VERSION=$target in .env eintragen …"
sed -i "s/^LEDGER_VERSION=.*/LEDGER_VERSION=$target/" .env

echo "4/4 wallet-rpc und ledger neu starten …"
docker compose -p "$PROJECT" up -d "${SERVICES[@]}"

sleep 5
echo
echo "Log (Startzeile zeigt Version und DB-Schema):"
container=$(docker compose -p "$PROJECT" ps -q ledger)
docker logs --tail 15 "$container" 2>&1 || true

cat <<EOF

Fertig: Ledger $current → $target.
Sicherung: ledger/data/$backup (löschen, wenn alles passt).
Zurück auf $current (nur zusammen mit der Sicherung, Migrationen gehen nur vorwärts):
  sudo docker compose -p $PROJECT stop ledger
  sudo cp ledger/data/$backup ledger/data/ledger.sqlite
  sudo rm -f ledger/data/ledger.sqlite-wal ledger/data/ledger.sqlite-shm
  sudo sed -i 's/^LEDGER_VERSION=.*/LEDGER_VERSION=$current/' .env
  sudo docker compose -p $PROJECT up -d ${SERVICES[*]}
EOF
