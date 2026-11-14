#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
# Misst für mehrere Thread-Zahlen Hashrate und Mehrverbrauch und schlägt Threads und Watt vor.
#
#   ./einmessen.sh            Stufenleiter über alle Kerne (siehe unten)
#   ./einmessen.sh 3 4        bestimmte Thread-Zahlen
#   WARMUP=300 WINDOW=180 ./einmessen.sh   Aufwärmen/Messen je Stufe in Sekunden
#
# Stufenleiter (P = Performance-, E = Effizienz-Kerne): lüfterlos P−1, P, P+E/2, alle; mit Lüfter P, P+E/2,
# alle (z. B. M4 mit 4 P + 6 E: 3, 4, 7, 10). Gemessen wird aufsteigend ohne Pause, es zählt der Dauerbetrieb.
# Ablauf: Leerlauf messen → je Stufe XMRig gegen den eigenen P2Pool starten, aufwärmen (lüfterlose Macs
# 5 Min., damit die Drosselung erfasst wird), dann Hashrate (XMRig-API) und Leistung (powermetrics) mitteln.
# Mehrverbrauch = (Last − Leerlauf) × 1,1 (Netzteil), aufgerundet (RAM misst powermetrics nicht).
# Vorschlag = Stufe mit dem höchsten Saldo aus rechnerischem Ertrag und Stromkosten (Kennzahlen vom Ledger:
# Difficulty und Blockbelohnung vom eigenen Node, lokaler Kurs, Tarif). Ohne Ledger-Kennzahlen: beste Hashrate
# je Watt (bei < 3 % Unterschied die höhere). Die ganze Tabelle wird angezeigt. Ergebnis: ~/.config/moneta/einmessung.json (Install/Kopplung nutzen es).
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
ecores=$(( ncpu - pcores ))

# Stufenleiter (Kandidaten) – aufsteigend, ohne doppelte, geprüft
ladder() {
  local half=$(( (ecores + 1) / 2 ))
  if [ "$fanless" = 1 ]; then
    echo $(( pcores > 1 ? pcores - 1 : 1 )) "$pcores" $(( pcores + half )) "$ncpu"
  elif [ "$ecores" -gt 0 ]; then
    echo "$pcores" $(( pcores + half )) "$ncpu"
  else
    echo $(( ncpu > 1 ? ncpu - 1 : 1 )) "$ncpu"
  fi
}
if [ $# -gt 0 ]; then raw=("$@"); else read -r -a raw <<< "$(ladder)"; fi
for n in "${raw[@]}"; do
  [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -ge 1 ] && [ "$n" -le "$ncpu" ] || die "Ungültige Thread-Zahl: $n (1–$ncpu)"
done
read -r -a candidates <<< "$(printf '%s\n' "${raw[@]}" | sort -n -u | tr '\n' ' ')"

if [ "$fanless" = 1 ]; then WARMUP="${WARMUP:-300}"; else WARMUP="${WARMUP:-90}"; fi
COOLDOWN="${COOLDOWN:-0}"   # aufsteigend messen: keine Pause nötig, gemessen wird der Dauerzustand
WINDOW="${WINDOW:-120}"
IDLE="${IDLE:-30}"
total=$(( IDLE + ${SETTLE:-20} + ${#candidates[@]} * (WARMUP + WINDOW + COOLDOWN) ))
say "Einmessen: Threads ${candidates[*]} von $ncpu ($pcores Performance, $ecores Effizienz) – Dauer etwa $(( (total + 59) / 60 )) Minuten"
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
  if [ "$COOLDOWN" -gt 0 ] && [ "$n" != "${candidates[${#candidates[@]}-1]}" ]; then
    echo "  abkühlen ${COOLDOWN} s …"
    sleep "$COOLDOWN"
  fi
done

say "Ergebnis"
mkdir -p "$CONF_DIR"
# Ertrag und Stromkosten je Stufe: Kennzahlen vom eigenen Ledger (Difficulty vom Node, lokaler Kurs, Tarif)
LEDGER="${LEDGER:-$( { [ -r "$CONF_DIR/ledger" ] && tr -d '[:space:]' < "$CONF_DIR/ledger"; } || true )}"
discovery=""
[ -n "$LEDGER" ] && discovery="$(curl -s -m 5 "$LEDGER/api/moneta" 2>/dev/null || true)"
python3 - "$idle_w" "$results" "$RESULT" "$ncpu" "$profile" "$discovery" <<'PY'
import json, math, sys, time
idle, results, out, ncpu, profile = float(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
try:
    eco = json.loads(sys.argv[6]).get("economics") if sys.argv[6] else None
except ValueError:
    eco = None
rows = []
for line in open(results):
    n, hr, load = line.split("\t")
    hr, load = float(hr), float(load)
    delta = max(load - idle, 0.1)
    extra = math.ceil(delta * 1.1)               # +10 % Netzteil, aufgerundet (RAM)
    r = {"threads": int(n), "hashrate": round(hr), "load_w": round(load, 2), "delta_w": round(delta, 2),
         "extra_w": extra, "h_per_w": round(hr / extra, 1)}
    if eco:
        r["eur_day"] = round(hr * eco["eur_per_hs_day"], 4)        # rechnerischer Ertrag je Tag
        r["cost_day"] = round(extra * eco["eur_per_w_day"], 4)     # Stromkosten je Tag
        r["net_day"] = round(r["eur_day"] - r["cost_day"], 4)
    rows.append(r)
rows.sort(key=lambda r: r["threads"])
if eco:
    # Grenznutzen: die Stufe mit dem höchsten Saldo – jede weitere Stufe bringt dann weniger Mehrertrag als
    # Mehrstrom kostet. Bei gleichem Saldo (± 0,1 ct/Tag) die mit weniger Watt.
    top = max(r["net_day"] for r in rows)
    choice = min((r for r in rows if r["net_day"] >= top - 0.001), key=lambda r: r["extra_w"])
    criterion = "höchster Saldo aus Ertrag und Strom"
else:
    best = max(r["h_per_w"] for r in rows)
    # beste Effizienz; bei < 3 % Unterschied die höhere Hashrate
    choice = max((r for r in rows if r["h_per_w"] >= best * 0.97), key=lambda r: r["hashrate"])
    criterion = "beste Hashrate je Watt (keine Kennzahlen vom Ledger)"
day = time.strftime("%d.%m.%Y")
de = lambda x, d=1: f"{x:.{d}f}".replace(".", ",")
hs = f"{choice['hashrate']:,}".replace(",", ".")
note = (f"Einmessung {day} (einmessen.sh, powermetrics): {de(choice['load_w'])} W Last bei {choice['threads']} "
        f"Threads ({hs} H/s) − {de(idle)} W Leerlauf = {de(choice['delta_w'])} W; "
        f"+10 % Netzteil, aufgerundet wegen RAM")
threads = "all" if choice["threads"] == ncpu else str(choice["threads"])
res = {"date": time.strftime("%Y-%m-%d %H:%M"), "idle_w": idle, "candidates": rows, "economics": eco,
       "choice": {"threads": threads, "watts": float(choice["extra_w"]), "note": note, "criterion": criterion},
       "profile": json.loads(profile)}
with open(out, "w") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)

head = "  Threads  Hashrate   Mehr W    H/W"
if eco:
    head += "   Ertrag €/Tag  Strom €/Tag  Saldo €/Tag  Δ Saldo"
print(head)
prev = None
for r in rows:
    line = f"  {r['threads']:>7}  {r['hashrate']:>6} H/s {r['extra_w']:>6}  {r['h_per_w']:>6.1f}"
    if eco:
        d = f"{de(r['net_day'] - prev['net_day'], 3):>8}" if prev else f"{'–':>8}"
        line += f"   {de(r['eur_day'], 3):>12}  {de(r['cost_day'], 3):>11}  {de(r['net_day'], 3):>11}  {d}"
    print(line + ("  ← Vorschlag" if r is choice else ""))
    prev = r
if eco:
    t = lambda ts: time.strftime("%d.%m. %H:%M", time.localtime(ts))
    diff = f"{eco['difficulty']:,}".replace(",", ".")
    print(f"\n  Grundlage: Difficulty {diff} (eigener Node, {t(eco['network_ts'])}), Blockbelohnung "
          f"{de(eco['reward_xmr'], 4)} XMR, Kurs {de(eco['price_eur'], 2)} € ({t(eco['price_ts'])}), "
          f"Tarif {de(eco['ct_per_kwh'], 2)} ct/kWh")
    if max(r["net_day"] for r in rows) < 0:
        print("  Hinweis: Bei diesen Werten liegt jede Stufe im Minus; vorgeschlagen ist die mit dem geringsten.")
print(f"\n  Vorschlag: Threads {threads} von {ncpu}, Mehrverbrauch {choice['extra_w']} W – {criterion}.")
print("  Jede andere Stufe kannst du im Installer wählen.")
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
