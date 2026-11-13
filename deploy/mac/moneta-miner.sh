#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
# Steuert XMRig als launchd-Agent. Wird von deploy/mac/install.sh eingerichtet und auch von der
# Menüleisten-App „Moneta Miner“ benutzt.
#
#   moneta-miner.sh start | stop | restart
#   moneta-miner.sh status            Zustand, Autostart, Threads
#   moneta-miner.sh status --plain    dasselbe als key=value (für die App)
#   moneta-miner.sh autostart on|off  XMRig beim Anmelden starten
#   moneta-miner.sh threads [N|all]   Thread-Zahl anzeigen bzw. setzen (läuft XMRig, startet er neu)
#   moneta-miner.sh log [-f]          letzte Zeilen des Logs (bzw. mitlesen)
set -euo pipefail

LABEL="${MONETA_LABEL:-moneta.xmrig}"
CONF_DIR="${CONF_DIR:-$HOME/.config/moneta}"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/Moneta"
LOG="$LOG_DIR/xmrig.log"
LOG_MAX_BYTES=$((10 * 1024 * 1024))
DOMAIN="gui/$(id -u)"

die() { echo "$*" >&2; exit 1; }
need_plist() { [ -f "$PLIST" ] || die "LaunchAgent fehlt: $PLIST – zuerst deploy/mac/install.sh ausführen"; }
loaded() { launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; }
pid() { launchctl print "$DOMAIN/$LABEL" 2>/dev/null | awk '$1 == "pid" && $2 == "=" {print $3; exit}'; }

cpu_count() { sysctl -n hw.ncpu 2>/dev/null || getconf _NPROCESSORS_ONLN; }

autostart_state() {
  [ -f "$PLIST" ] || { echo 0; return; }
  if [ "$(plutil -extract RunAtLoad raw -o - "$PLIST" 2>/dev/null)" = "true" ]; then echo 1; else echo 0; fi
}

threads_state() {
  local t=""
  [ -r "$CONF_DIR/threads" ] && t="$(tr -d '[:space:]' < "$CONF_DIR/threads")"
  echo "${t:-all}"
}

rotate_log() {
  mkdir -p "$LOG_DIR"
  if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt "$LOG_MAX_BYTES" ]; then
    mv -f "$LOG" "$LOG.1"
  fi
}

start() {
  need_plist
  rotate_log
  loaded || launchctl bootstrap "$DOMAIN" "$PLIST"
  [ -n "$(pid)" ] || launchctl kickstart "$DOMAIN/$LABEL" || true   # Erfolg zeigt die PID-Prüfung
  local p=""
  for _ in 1 2 3 4 5 6; do
    p="$(pid)"
    [ -n "$p" ] && break
    sleep 0.5
  done
  if [ -z "$p" ]; then
    echo "XMRig ist nicht gestartet. Letzte Log-Zeilen:" >&2
    tail -n 5 "$LOG" >&2 2>/dev/null || true
    exit 1
  fi
  echo "XMRig läuft (PID $p)."
}

stop() {
  if loaded; then
    launchctl bootout "$DOMAIN/$LABEL"
  fi
  echo "XMRig gestoppt."
}

restart() {
  if [ -n "$(pid)" ]; then
    rotate_log
    launchctl kickstart -k "$DOMAIN/$LABEL"
    echo "XMRig neu gestartet."
  else
    start
  fi
}

status() {
  local p state
  p="$(pid)"
  if [ -n "$p" ]; then state=running; else state=stopped; fi
  if [ "${1:-}" = "--plain" ]; then
    printf 'state=%s\npid=%s\nautostart=%s\nthreads=%s\ncpus=%s\n' \
      "$state" "$p" "$(autostart_state)" "$(threads_state)" "$(cpu_count)"
    return
  fi
  if [ "$state" = running ]; then echo "XMRig läuft (PID $p)"; else echo "XMRig gestoppt"; fi
  if [ "$(autostart_state)" = 1 ]; then echo "Autostart: an"; else echo "Autostart: aus"; fi
  echo "Threads:   $(threads_state) (von $(cpu_count))"
  echo "Log:       $LOG"
}

autostart() {
  need_plist
  case "${1:-}" in
    on)  plutil -replace RunAtLoad -bool true "$PLIST";  echo "Autostart an (ab der nächsten Anmeldung)." ;;
    off) plutil -replace RunAtLoad -bool false "$PLIST"; echo "Autostart aus." ;;
    *)   die "Aufruf: $0 autostart on|off" ;;
  esac
}

threads() {
  local n="${1:-}"
  if [ -z "$n" ]; then threads_state; return; fi
  if [ "$n" != all ]; then
    case "$n" in *[!0-9]*) die "Thread-Zahl muss eine Zahl oder 'all' sein" ;; esac
    { [ "$n" -ge 1 ] && [ "$n" -le "$(cpu_count)" ]; } || die "Thread-Zahl muss zwischen 1 und $(cpu_count) liegen"
  fi
  mkdir -p "$CONF_DIR"
  echo "$n" > "$CONF_DIR/threads"
  echo "Threads: $n"
  if [ -n "$(pid)" ]; then restart; fi
}

log() {
  [ -f "$LOG" ] || die "Noch kein Log: $LOG"
  if [ "${1:-}" = "-f" ]; then tail -n 20 -f "$LOG"; else tail -n "${1:-50}" "$LOG"; fi
}

cmd="${1:-status}"
[ $# -gt 0 ] && shift
case "$cmd" in
  start|stop|restart|status|autostart|threads|log) "$cmd" "$@" ;;
  -h|--help|help) sed -n '3,11p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) die "Unbekannter Befehl: $cmd (start|stop|restart|status|autostart|threads|log)" ;;
esac
