#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
# Misst für mehrere Thread-Zahlen Hashrate und Mehrverbrauch und schlägt Threads und Watt vor.
#
#   ./einmessen.sh            Kandidaten aus dem Geräteprofil (profil.sh)
#   ./einmessen.sh 3 4        bestimmte Thread-Zahlen
#   WARMUP=300 WINDOW=300 ./einmessen.sh   Aufwärmen/Messen je Kandidat in Sekunden
#
# Ablauf: Leerlauf messen → je Kandidat XMRig gegen den eigenen P2Pool starten, aufwärmen (lüfterlose Macs
# 5 Min., damit die Drosselung erfasst wird), dann Hashrate (XMRig-API) und Leistung (powermetrics) mitteln.
# Mehrverbrauch = (Last − Leerlauf) × 1,1 (Netzteil), aufgerundet (RAM misst powermetrics nicht).
# Vorschlag = beste Hashrate je Watt. Ergebnis: ~/.config/moneta/einmessung.json (Install/Kopplung nutzen es).
#
# Voraussetzungen: Netzteil angeschlossen, Mac während der Messung nicht benutzen, sudo (powermetrics).
# Die Messung mint bereits über P2Pool; ein noch nicht freigegebener Rechner wird vom Ledger nicht erfasst.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd -P)"
CONF_DIR="${CONF_DIR:-$HOME/.config/moneta}"
RESULT="$CONF_DIR/einmessung.json"
API_PORT="${MEASURE_API_PORT:-18001}"
API_TOKEN="einmessen-$$"
CTL="$HOME/Library/Application Support/Moneta/moneta-miner.sh"

die() { printf '✗ %s\n' "$*" >&2; exit 1; }
say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

POOL="${POOL:-$( { [ -r "$CONF_DIR/pool" ] && tr -d '[:space:]' < "$CONF_DIR/pool"; } || true )}"
[ -n "$POOL" ] || die "Pool-Adresse fehlt (~/.config/moneta/pool) – zuerst install.sh ausführen"
XMRIG="${XMRIG:-$(command -v xmrig || true)}"
for candidate in /opt/homebrew/bin/xmrig /usr/local/bin/xmrig; do
  [ -n "$XMRIG" ] && break
  [ -x "$candidate" ] && XMRIG="$candidate"
done
[ -n "$XMRIG" ] || die "xmrig nicht gefunden – brew install xmrig"
command -v python3 >/dev/null || die "python3 fehlt (kommt mit den Command Line Tools: xcode-select --install)"
pmset -g batt 2>/dev/null | grep -q "AC Power" || die "Bitte das Netzteil anschließen (sonst pausiert XMRig)"

profile="$("$DIR/profil.sh")"
read -r ncpu pcores fanless < <(python3 -c 'import json,sys; p=json.loads(sys.argv[1]); c=p["cores"];
print(c["total"], c["performance"] or c["total"], int(p["fanless"]))' "$profile")

if [ $# -gt 0 ]; then
  candidates=("$@")
elif [ "$fanless" = 1 ]; then
  candidates=($(( pcores > 1 ? pcores - 1 : 1 )) "$pcores")
else
  candidates=("$ncpu" "$pcores")
fi
# doppelte entfernen, prüfen
uniq=()
for n in "${candidates[@]}"; do
  [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -ge 1 ] && [ "$n" -le "$ncpu" ] || die "Ungültige Thread-Zahl: $n (1–$ncpu)"
  case " ${uniq[*]-} " in *" $n "*) ;; *) uniq+=("$n") ;; esac
done
candidates=("${uniq[@]}")

if [ "$fanless" = 1 ]; then WARMUP="${WARMUP:-300}"; COOLDOWN="${COOLDOWN:-120}"; else WARMUP="${WARMUP:-60}"; COOLDOWN="${COOLDOWN:-60}"; fi
WINDOW="${WINDOW:-180}"
IDLE="${IDLE:-30}"
total=$(( IDLE + ${SETTLE:-20} + ${#candidates[@]} * (WARMUP + WINDOW + COOLDOWN) ))
say "Einmessen: Threads ${candidates[*]} – Dauer etwa $(( (total + 59) / 60 )) Minuten"
echo "  Pool $POOL, XMRig $("$XMRIG" --version 2>/dev/null | head -1 || echo "?")"
echo "  Bitte den Mac währenddessen nicht benutzen (Leerlauf und Last werden mit powermetrics gemessen)."

echo "  powermetrics braucht sudo:"
sudo -v
( while sleep 50; do sudo -n true 2>/dev/null || exit; done ) &
keeper=$!

was_running=false
if [ -x "$CTL" ] && "$CTL" status --plain 2>/dev/null | grep -q '^state=running'; then
  was_running=true
  "$CTL" stop >/dev/null
  echo "  XMRig-Agent für die Messung gestoppt."
fi
xpid=""
work="$(mktemp -d)"
cleanup() {
  [ -n "$xpid" ] && kill "$xpid" 2>/dev/null || true
  kill "$keeper" 2>/dev/null || true
  rm -rf "$work"
  if [ "$was_running" = true ]; then "$CTL" start >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT

# Durchschnittsleistung (W) über n Sekunden; powermetrics meldet "Combined Power (CPU + GPU + ANE): 1234 mW"
power() {
  sudo -n powermetrics --samplers cpu_power -i 1000 -n "$1" 2>/dev/null \
    | awk '/Combined Power/ {s+=$(NF-1); n++} END {if (n) printf "%.2f\n", s/n/1000; else print ""}'
}

say "Leerlauf"
sleep "${SETTLE:-20}"
idle_w="$(power "$IDLE")"
[ -n "$idle_w" ] || die "powermetrics lieferte keine Werte"
echo "  Leerlauf: $idle_w W"

results="$work/results.tsv"
: > "$results"
for n in "${candidates[@]}"; do
  say "$n Threads: aufwärmen ${WARMUP} s, messen ${WINDOW} s"
  "$XMRIG" -o "$POOL" -t "$n" --cpu-priority 0 --no-color --http-host 127.0.0.1 --http-port "$API_PORT" \
    --http-access-token "$API_TOKEN" > "$work/xmrig-$n.log" 2>&1 &
  xpid=$!
  sleep "$WARMUP"
  kill -0 "$xpid" 2>/dev/null || die "XMRig ist beendet – siehe Log: $(tail -n 3 "$work/xmrig-$n.log")"
  power "$WINDOW" > "$work/power-$n" &
  ppid_=$!
  : > "$work/hr-$n"
  while kill -0 "$ppid_" 2>/dev/null; do
    curl -s -m 3 -H "Authorization: Bearer $API_TOKEN" "http://127.0.0.1:$API_PORT/2/summary" \
      | python3 -c 'import json,sys
d=json.load(sys.stdin); v=(d.get("hashrate") or {}).get("total") or []
v=[x for x in v[:1] if x]; print(v[0] if v and not d.get("paused") else "")' >> "$work/hr-$n" 2>/dev/null || true
    sleep 15
  done
  wait "$ppid_" || true
  kill "$xpid" 2>/dev/null || true
  wait "$xpid" 2>/dev/null || true
  xpid=""
  load_w="$(cat "$work/power-$n")"
  hr="$(awk 'NF && $1 > 0 {s+=$1; n++} END {if (n) printf "%.0f\n", s/n}' "$work/hr-$n")"
  [ -n "$load_w" ] && [ -n "$hr" ] || die "Keine Messwerte für $n Threads (Pool erreichbar? Log: $work/xmrig-$n.log)"
  printf '%s\t%s\t%s\n' "$n" "$hr" "$load_w" >> "$results"
  echo "  $n Threads: $hr H/s bei $load_w W"
  if [ "$n" != "${candidates[${#candidates[@]}-1]}" ]; then
    echo "  abkühlen ${COOLDOWN} s …"
    sleep "$COOLDOWN"
  fi
done

say "Ergebnis"
mkdir -p "$CONF_DIR"
python3 - "$idle_w" "$results" "$RESULT" "$ncpu" "$profile" <<'PY'
import json, math, sys, time
idle, results, out, ncpu, profile = float(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
rows = []
for line in open(results):
    n, hr, load = line.split("\t")
    hr, load = float(hr), float(load)
    delta = max(load - idle, 0.1)
    extra = math.ceil(delta * 1.1)               # +10 % Netzteil, aufgerundet (RAM)
    rows.append({"threads": int(n), "hashrate": round(hr), "load_w": round(load, 2), "delta_w": round(delta, 2),
                 "extra_w": extra, "h_per_w": round(hr / extra, 1)})
best = max(r["h_per_w"] for r in rows)
# beste Effizienz; bei < 3 % Unterschied die höhere Hashrate
choice = max((r for r in rows if r["h_per_w"] >= best * 0.97), key=lambda r: r["hashrate"])
day = time.strftime("%d.%m.%Y")
de = lambda x: f"{x:.1f}".replace(".", ",")
hs = f"{choice['hashrate']:,}".replace(",", ".")
note = (f"Einmessung {day} (einmessen.sh, powermetrics): {de(choice['load_w'])} W Last bei {choice['threads']} "
        f"Threads ({hs} H/s) − {de(idle)} W Leerlauf = {de(choice['delta_w'])} W; "
        f"+10 % Netzteil, aufgerundet wegen RAM")
threads = "all" if choice["threads"] == ncpu else str(choice["threads"])
res = {"date": time.strftime("%Y-%m-%d %H:%M"), "idle_w": idle, "candidates": rows,
       "choice": {"threads": threads, "watts": float(choice["extra_w"]), "note": note},
       "profile": json.loads(profile)}
with open(out, "w") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("  Threads  Hashrate   Last W  Mehr W   H/W")
for r in rows:
    mark = "  ← Vorschlag" if r is choice else ""
    print(f"  {r['threads']:>7}  {r['hashrate']:>6} H/s {r['load_w']:>7.1f} {r['extra_w']:>6}  {r['h_per_w']:>6.1f}{mark}")
print(f"\n  Vorschlag: Threads {threads}, Mehrverbrauch {choice['extra_w']} W")
print(f"  Notiz: {note}")
PY
chmod 600 "$RESULT"
echo "  Gespeichert: $RESULT"

threads="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["choice"]["threads"])' "$RESULT")"
if [ -t 0 ]; then
  read -r -p "  Threads auf $threads setzen? (j/n) [j]: " a
  case "${a:-j}" in
    [jJyY]*)
      if [ -x "$CTL" ]; then "$CTL" threads "$threads" >/dev/null; else echo "$threads" > "$CONF_DIR/threads"; fi
      echo "  Threads: $threads" ;;
  esac
fi
echo "  Für den Ledger: Watt und Notiz bei der Freigabe übernehmen (Kopplung schickt sie als Vorschlag mit)."
