#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
# Misst den durchschnittlichen Chip-Verbrauch (CPU+GPU+ANE) mit powermetrics.
#
#   ./strom-messen.sh        30 Sekunden
#   ./strom-messen.sh 60     60 Sekunden
#
# Vorgehen: einmal mit laufendem XMRig (nach ~1 Min. Anlauf) und einmal im Leerlauf messen.
# Mehrverbrauch = Last − Leerlauf, +10 % Netzteilverluste, wegen RAM leicht aufrunden.
# Ergebnis als watts/note in config.toml des Ledgers eintragen (docs/de/setup-mac.md; EN: docs/en/setup-mac.md).
set -euo pipefail
N="${1:-30}"
sudo powermetrics --samplers cpu_power -i 1000 -n "$N" \
  | awk '/Combined Power/ {s+=$(NF-1); n++} END {if (n) printf "Durchschnitt: %.1f W (%d Messwerte)\n", s/n/1000, n; else print "keine Messwerte"}'
