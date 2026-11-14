#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
# Richtet einen Mac als Miner ein: XMRig (Homebrew), Pool-Adresse, API-Token, launchd-Agent und die
# Menüleisten-App „Moneta Miner“ (wird hier lokal aus dem Quellcode gebaut). Kann gefahrlos erneut
# ausgeführt werden, z. B. nach einem git pull; vorhandene Einstellungen bleiben erhalten.
#
#   deploy/mac/install.sh               einrichten bzw. aktualisieren
#   deploy/mac/install.sh --uninstall   Agent, App und Skripte entfernen (Einstellungen und Log bleiben)
#
# Ohne Rückfragen (alle optional): POOL=<NAS-IP>:3333 THREADS=3 TOKEN=<vorhandenes Token>
#   AUTOSTART=j|n FIREWALL=j|n START=j|n deploy/mac/install.sh
#
# Anleitung: docs/de/setup-mac.md (EN: docs/en/setup-mac.md)
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd -P)"
CONF_DIR="$HOME/.config/moneta"
SUPPORT_DIR="$HOME/Library/Application Support/Moneta"
AGENT_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/Moneta"
APP_DIR="$HOME/Applications/Moneta Miner.app"
MINER_LABEL="moneta.xmrig"
MENU_LABEL="moneta.menubar"
API_PORT=18000
FW=/usr/libexec/ApplicationFirewall/socketfilterfw
DOMAIN="gui/$(id -u)"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*" >&2; }
die()  { printf '\n✗ %s\n' "$*" >&2; exit 1; }

# ask "Frage" "Vorgabe" [Umgebungsvariable] – ohne Terminal gilt die Vorgabe
ask() {
  local q="$1" def="${2:-}" preset="${3:-}" a
  if [ -n "$preset" ]; then echo "$preset"; return; fi
  if [ ! -t 0 ]; then echo "$def"; return; fi
  read -r -p "  $q${def:+ [$def]}: " a
  echo "${a:-$def}"
}
yes_no() {  # yes_no "Frage" j|n [Umgebungsvariable]
  local a
  a="$(ask "$1 (j/n)" "$2" "${3:-}")"
  case "$a" in [jJyY]*) return 0 ;; *) return 1 ;; esac
}

xml_escape() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' <<< "$1"; }

# Symlinks auflösen (Homebrew verlinkt bin/xmrig in den Cellar; die Firewall-Freigabe hängt am echten Pfad)
real_path() {
  local p="$1" t
  while [ -L "$p" ]; do
    t="$(readlink "$p")"
    case "$t" in /*) p="$t" ;; *) p="$(dirname "$p")/$t" ;; esac
  done
  echo "$(cd "$(dirname "$p")" && pwd -P)/$(basename "$p")"
}

agent_off() { launchctl bootout "$DOMAIN/$1" >/dev/null 2>&1 || true; }

uninstall() {
  say "Moneta Miner entfernen"
  agent_off "$MENU_LABEL"
  agent_off "$MINER_LABEL"
  rm -f "$AGENT_DIR/$MINER_LABEL.plist" "$AGENT_DIR/$MENU_LABEL.plist"
  rm -rf "$APP_DIR" "$SUPPORT_DIR"
  ok "launchd-Agents, App und Skripte entfernt"
  echo "  Behalten: $CONF_DIR (Pool, Token, Threads), $LOG_DIR und XMRig (brew uninstall xmrig)."
  echo "  Firewall-Freigabe ggf. entfernen: Pfad mit 'sudo $FW --listapps' suchen, dann"
  echo "    sudo $FW --remove <Pfad>"
}

# ---------------------------------------------------------------------------------------------------------

case "${1:-}" in
  --uninstall) uninstall; exit 0 ;;
  "") ;;
  -h|--help) sed -n '3,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) die "Unbekannte Option: $1 (--uninstall, --help)" ;;
esac

[ "$(uname -s)" = Darwin ] || die "Dieses Skript ist für macOS. Linux: siehe docs/de/setup-mac.md."
macos_major="$(sw_vers -productVersion | cut -d. -f1)"
[ "$macos_major" -ge 13 ] || die "macOS 13 (Ventura) oder neuer nötig – gefunden: $(sw_vers -productVersion)"
[ "$(uname -m)" = arm64 ] || warn "Kein Apple Silicon – Moneta ist dafür getestet; Intel-Macs sollten aber laufen."

# --- 1. Werkzeuge ------------------------------------------------------------------------------------------
say "1/6 Werkzeuge"
if ! xcode-select -p >/dev/null 2>&1; then
  xcode-select --install || true
  die "Die Command Line Tools werden installiert (Fenster von macOS). Danach install.sh erneut starten."
fi
ok "Command Line Tools: $(xcode-select -p)"

BREW="$(command -v brew || true)"
for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
  [ -n "$BREW" ] && break
  [ -x "$candidate" ] && BREW="$candidate"
done
if [ -z "$BREW" ]; then
  echo "  Homebrew fehlt. Offizielles Installationsskript von brew.sh (fragt nach deinem Mac-Passwort)."
  yes_no "Homebrew jetzt installieren?" j || die "Ohne Homebrew geht es nicht weiter: https://brew.sh"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  BREW=/opt/homebrew/bin/brew
  [ -x "$BREW" ] || BREW=/usr/local/bin/brew
  [ -x "$BREW" ] || die "Homebrew nach der Installation nicht gefunden."
  if ! grep -qs 'brew shellenv' "$HOME/.zprofile"; then
    echo "eval \"\$($BREW shellenv)\"" >> "$HOME/.zprofile"
    ok "Homebrew in ~/.zprofile eingetragen"
  fi
fi
eval "$("$BREW" shellenv)"
BREW_PREFIX="$("$BREW" --prefix)"
ok "Homebrew: $BREW_PREFIX"

if "$BREW" list --formula xmrig >/dev/null 2>&1; then
  ok "XMRig vorhanden ($("$BREW" list --versions xmrig))"
else
  "$BREW" install xmrig    # Homebrew-Build: DONATE 0 %
  ok "XMRig installiert ($("$BREW" list --versions xmrig))"
fi
XMRIG_BIN="$BREW_PREFIX/bin/xmrig"

# --- 2. Einstellungen --------------------------------------------------------------------------------------
say "2/6 Einstellungen ($CONF_DIR)"
mkdir -p "$CONF_DIR"
chmod 700 "$CONF_DIR"

old_pool="$( { [ -r "$CONF_DIR/pool" ] && tr -d '[:space:]' < "$CONF_DIR/pool"; } || true )"
while :; do
  pool="$(ask "P2Pool-Stratum (<NAS-IP>:3333)" "$old_pool" "${POOL:-}")"
  if [[ "$pool" =~ ^[A-Za-z0-9.-]+:[0-9]{1,5}$ ]]; then break; fi
  [ -t 0 ] && [ -z "${POOL:-}" ] || die "Ungültige Pool-Adresse: '$pool' (erwartet Host:Port)"
  warn "Bitte als Host:Port angeben, z. B. 192.168.1.10:3333"
done
echo "$pool" > "$CONF_DIR/pool"
ok "Pool: $pool"

token_file="$CONF_DIR/xmrig-token"
if [ -s "$token_file" ] && [ -z "${TOKEN:-}" ]; then
  ok "API-Token vorhanden – bleibt unverändert"
else
  echo "  Steht für diesen Mac schon ein [[miner]]-Eintrag mit token in der config.toml des Ledgers,"
  echo "  füge das Token hier ein. Sonst Enter: Es wird ein neues erzeugt."
  token="$(ask "Vorhandenes Token" "" "${TOKEN:-}")"
  if [ -z "$token" ]; then
    token="$(openssl rand -hex 16)"
    ok "Neues API-Token erzeugt"
  elif ! [[ "$token" =~ ^[A-Za-z0-9._~-]{8,128}$ ]]; then
    die "Das Token darf nur Buchstaben, Ziffern und . _ ~ - enthalten (8–128 Zeichen)."
  fi
  (umask 077; echo "$token" > "$token_file")
  ok "API-Token gespeichert"
fi
chmod 600 "$token_file"
token="$(tr -d '[:space:]' < "$token_file")"

ncpu="$(sysctl -n hw.ncpu)"
pcores="$(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null || echo "?")"
ecores="$(sysctl -n hw.perflevel1.physicalcpu 2>/dev/null || echo "?")"
old_threads="$( { [ -r "$CONF_DIR/threads" ] && tr -d '[:space:]' < "$CONF_DIR/threads"; } || true )"
echo "  $ncpu Kerne ($pcores Performance, $ecores Effizienz). Lüfterlose Macs drosseln unter Dauerlast –"
echo "  dort weniger Threads wählen (Referenzwerte in docs/de/setup-mac.md)."
while :; do
  threads="$(ask "Threads (Zahl oder all)" "${old_threads:-all}" "${THREADS:-}")"
  if [ "$threads" = all ] || { [[ "$threads" =~ ^[0-9]+$ ]] && [ "$threads" -ge 1 ] && [ "$threads" -le "$ncpu" ]; }; then
    break
  fi
  [ -t 0 ] && [ -z "${THREADS:-}" ] || die "Ungültige Thread-Zahl: '$threads' (1–$ncpu oder all)"
  warn "Bitte eine Zahl von 1 bis $ncpu oder 'all'"
done
echo "$threads" > "$CONF_DIR/threads"
ok "Threads: $threads"

# --- 3. Skripte und launchd-Agent --------------------------------------------------------------------------
say "3/6 Skripte und launchd-Agent"
mkdir -p "$SUPPORT_DIR" "$AGENT_DIR" "$LOG_DIR"
install -m 755 "$SRC_DIR/xmrig-start.sh" "$SUPPORT_DIR/xmrig-start.sh"
install -m 755 "$SRC_DIR/moneta-miner.sh" "$SUPPORT_DIR/moneta-miner.sh"
ok "Skripte nach $SUPPORT_DIR kopiert"

miner_plist="$AGENT_DIR/$MINER_LABEL.plist"
run_at_load=false
if [ -f "$miner_plist" ] && [ "$(plutil -extract RunAtLoad raw -o - "$miner_plist" 2>/dev/null)" = true ]; then
  run_at_load=true
fi
default_autostart=n; [ "$run_at_load" = true ] && default_autostart=j
if yes_no "XMRig beim Anmelden automatisch starten?" "$default_autostart" "${AUTOSTART:-}"; then
  run_at_load=true
else
  run_at_load=false
fi

was_running=false
if launchctl print "$DOMAIN/$MINER_LABEL" 2>/dev/null | grep -q 'pid = '; then was_running=true; fi
agent_off "$MINER_LABEL"

cat > "$miner_plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<!-- Erzeugt von Moneta deploy/mac/install.sh – Änderungen dort vornehmen und install.sh erneut ausführen. -->
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$MINER_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$(xml_escape "$SUPPORT_DIR/xmrig-start.sh")</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>$(xml_escape "$BREW_PREFIX/bin"):/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>WorkingDirectory</key>
  <string>$(xml_escape "$SUPPORT_DIR")</string>
  <key>RunAtLoad</key>
  <$run_at_load/>
  <!-- nach einem Absturz neu starten, nicht nach einem regulären Stopp -->
  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>
  <key>ThrottleInterval</key>
  <integer>60</integer>
  <!-- Standard statt Background: Background würde macOS auf die Effizienzkerne drosseln lassen -->
  <key>ProcessType</key>
  <string>Standard</string>
  <key>StandardOutPath</key>
  <string>$(xml_escape "$LOG_DIR/xmrig.log")</string>
  <key>StandardErrorPath</key>
  <string>$(xml_escape "$LOG_DIR/xmrig.log")</string>
</dict>
</plist>
EOF
plutil -lint -s "$miner_plist"
# Geladen wird der Agent beim Start (moneta-miner.sh start) bzw. bei der nächsten Anmeldung.
ok "launchd-Agent $MINER_LABEL (Autostart: $([ "$run_at_load" = true ] && echo an || echo aus))"

# --- 4. Menüleisten-App ------------------------------------------------------------------------------------
say '4/6 Menüleisten-App „Moneta Miner“'
app_built=false
if ! xcrun --find swiftc >/dev/null 2>&1; then
  warn "swiftc fehlt – App wird übersprungen (Command Line Tools aktualisieren: softwareupdate --list)."
else
  build_dir="$(mktemp -d)"
  trap 'rm -rf "$build_dir"' EXIT
  app_tmp="$build_dir/Moneta Miner.app"
  mkdir -p "$app_tmp/Contents/MacOS"
  if xcrun swiftc -O -swift-version 5 -parse-as-library \
       -target "$(uname -m)-apple-macos13.0" \
       -o "$app_tmp/Contents/MacOS/MonetaMiner" "$SRC_DIR/MonetaMiner/MonetaMiner.swift"; then
    cp "$SRC_DIR/MonetaMiner/Info.plist" "$app_tmp/Contents/Info.plist"
    # ad-hoc signiert; lokal gebaut, daher ohne Quarantäne-Attribut und ohne Gatekeeper-Rückfrage
    codesign --force --sign - "$app_tmp" >/dev/null 2>&1 || warn "codesign fehlgeschlagen"
    agent_off "$MENU_LABEL"
    pkill -x MonetaMiner >/dev/null 2>&1 || true
    mkdir -p "$(dirname "$APP_DIR")"
    rm -rf "$APP_DIR"
    mv "$app_tmp" "$APP_DIR"
    app_built=true
    ok "App gebaut: $APP_DIR"
  else
    warn "Die App ließ sich nicht bauen – XMRig lässt sich trotzdem mit moneta-miner.sh steuern."
  fi
fi

if [ "$app_built" = true ]; then
  menu_plist="$AGENT_DIR/$MENU_LABEL.plist"
  cat > "$menu_plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<!-- Erzeugt von Moneta deploy/mac/install.sh: startet die Menüleisten-App beim Anmelden. -->
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$MENU_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(xml_escape "$APP_DIR/Contents/MacOS/MonetaMiner")</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>LimitLoadToSessionType</key>
  <string>Aqua</string>
  <key>ProcessType</key>
  <string>Interactive</string>
</dict>
</plist>
EOF
  plutil -lint -s "$menu_plist"
  launchctl bootstrap "$DOMAIN" "$menu_plist"
  ok "App startet beim Anmelden und läuft jetzt (Symbol in der Menüleiste)"
fi

# --- 5. Firewall -------------------------------------------------------------------------------------------
say "5/6 macOS-Firewall"
xmrig_real="$(real_path "$XMRIG_BIN")"
if "$FW" --getglobalstate 2>/dev/null | grep -qi enabled; then
  echo "  Die Firewall ist an. Der Ledger auf der NAS fragt die XMRig-API (Port $API_PORT) ab;"
  echo "  dafür braucht xmrig eine Freigabe für eingehende Verbindungen (zwei sudo-Befehle)."
  if yes_no "Freigabe jetzt einrichten?" j "${FIREWALL:-}"; then
    sudo "$FW" --add "$xmrig_real"
    sudo "$FW" --unblockapp "$xmrig_real"
    ok "Freigabe für $xmrig_real"
    echo "  Hinweis: Nach 'brew upgrade xmrig' ändert sich der Pfad – dann install.sh erneut ausführen."
  else
    echo "  Später von Hand:"
    echo "    sudo $FW --add \"$xmrig_real\""
    echo "    sudo $FW --unblockapp \"$xmrig_real\""
  fi
else
  ok "Firewall ist aus – keine Freigabe nötig"
fi

# --- 6. Eintrag für den Ledger -----------------------------------------------------------------------------
say "6/6 Eintrag für den Ledger (config.toml auf der NAS)"
ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo '<IP-DES-RECHNERS>')"
name="$(scutil --get ComputerName 2>/dev/null || hostname -s)"
name="${name//\\/\\\\}"; name="${name//\"/\\\"}"   # für TOML
block_file="$CONF_DIR/ledger-miner.toml"
(umask 077; cat > "$block_file" <<EOF
[[miner]]
name = "$name"
url = "http://$ip:$API_PORT"
token = "$token"
watts = <MEHRVERBRAUCH_W>   # erst nach der Messung eintragen (deploy/mac/strom-messen.sh)
note = "gemessen am TT.MM.JJJJ mit powermetrics: … W Last − … W Leerlauf; +10 % Netzteil"
EOF
)
sed 's/^/    /' "$block_file"
cat <<EOF

  Gespeichert in $block_file.
  Reihenfolge: IP $ip im Router fest vergeben → Mehrverbrauch messen → Block in config.toml einfügen
  (watts ersetzen) → Ledger neu starten. Die Watt werden je Erfassung festgeschrieben; ein falscher Wert
  lässt sich später nicht korrigieren. Der Ledger zählt Mining-Zeit erst ab dem Eintrag.
  Steht der Mac schon in der config.toml, nur prüfen, ob token und url übereinstimmen.
EOF

say "Fertig"
ctl="$SUPPORT_DIR/moneta-miner.sh"
if [ "$was_running" = true ]; then
  "$ctl" start
elif yes_no "XMRig jetzt starten?" n "${START:-}"; then
  "$ctl" start
fi
cat <<EOF
  Steuerung: Menüleiste → Moneta Miner, oder im Terminal:
    "$ctl" start|stop|status|threads N|autostart on|off|log
EOF
