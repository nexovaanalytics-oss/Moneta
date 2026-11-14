#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
# Gibt das Geräteprofil dieses Macs als JSON aus: Modell, Chip, Kerne, lüfterlos, Thread-Empfehlung.
# Wird von install.sh und einmessen.sh benutzt und bei der Kopplung an den Ledger gemeldet.
#
#   ./profil.sh            JSON
#   ./profil.sh threads    nur die empfohlene Thread-Zahl (Zahl oder all)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd -P)"
TABLE="${PROFILE_TABLE:-$DIR/profile.tsv}"

chip="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo unbekannt)"
model="$(sysctl -n hw.model 2>/dev/null || echo unbekannt)"
ncpu="$(sysctl -n hw.ncpu 2>/dev/null || getconf _NPROCESSORS_ONLN)"
pcores="$(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null || echo "")"
ecores="$(sysctl -n hw.perflevel1.physicalcpu 2>/dev/null || echo "")"
os="macOS $(sw_vers -productVersion 2>/dev/null || echo "?")"
# Modellname („MacBook Air“, „MacBook Pro“, „Mac mini“ …) aus system_profiler
model_name="$(system_profiler SPHardwareDataType -json 2>/dev/null \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["SPHardwareDataType"][0].get("machine_name",""))' \
  2>/dev/null || true)"

fanless=0
case "$model_name" in "MacBook Air"*) case "$chip" in Apple*) fanless=1 ;; esac ;; esac

threads="" source=""
if [ -r "$TABLE" ]; then
  while IFS=$'\t' read -r t_chip t_fanless t_threads t_source; do
    case "$t_chip" in ""|\#*) continue ;; esac
    if [ "$t_chip" = "$chip" ] && [ "$t_fanless" = "$fanless" ]; then
      threads="$t_threads"; source="Profiltabelle: $t_source"; break
    fi
  done < "$TABLE"
fi
if [ -z "$threads" ]; then
  if [ "$fanless" = 1 ] && [ -n "$pcores" ]; then
    threads=$(( pcores > 1 ? pcores - 1 : 1 ))
    source="Faustregel: lüfterlos → Performance-Kerne − 1 (drosselt sonst unter Dauerlast)"
  else
    threads=all
    source="Faustregel: mit Lüfter → alle Kerne"
  fi
fi

if [ "${1:-}" = threads ]; then
  echo "$threads"
  exit 0
fi

python3 - "$model" "$model_name" "$chip" "$ncpu" "$pcores" "$ecores" "$fanless" "$os" "$threads" "$source" <<'PY'
import json, sys
model, name, chip, ncpu, p, e, fanless, osv, threads, source = sys.argv[1:]
num = lambda v: int(v) if v.isdigit() else None
print(json.dumps({
    "model": model, "model_name": name, "chip": chip, "os": osv, "fanless": fanless == "1",
    "cores": {"total": num(ncpu), "performance": num(p), "efficiency": num(e)},
    "suggestion": {"threads": threads, "source": source},
}, ensure_ascii=False))
PY
