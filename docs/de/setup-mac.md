# Setup Rechner (macOS)

🌐 **Deutsch** · [English](../en/setup-mac.md) · [Français](../fr/setup-mac.md) · [Español](../es/setup-mac.md)

Beschrieben für macOS mit Apple Silicon; unter Linux sind die Schritte analog (XMRig aus der
Paketverwaltung bzw. von xmrig.com, Strommessung z. B. mit Messsteckdose).

## 1. XMRig installieren

```bash
# Homebrew, falls `brew` fehlt
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

brew install xmrig          # Homebrew-Build: DONATE 0 %
```

## 2. Pool-Adresse und API-Token

```bash
ipconfig getifaddr en0                      # IP des Rechners – im Router fest vergeben
mkdir -p ~/.config/moneta
echo '<NAS-IP>:3333' > ~/.config/moneta/pool
openssl rand -hex 16 > ~/.config/moneta/xmrig-token
chmod 600 ~/.config/moneta/xmrig-token
cat ~/.config/moneta/xmrig-token            # gehört als token in die config.toml des Ledgers
```

## 3. Hashrate und Mehrverbrauch messen

Tab 1 – Last erzeugen (ohne Pool), mit der Thread-Zahl, die später laufen soll:

```bash
xmrig --bench=10M          # alle Kerne
xmrig --bench=10M -t 3     # z. B. 3 Threads
```

Tab 2 – nach ~1 Minute messen, danach XMRig beenden und im Leerlauf erneut messen:

```bash
deploy/mac/strom-messen.sh
```

Mehrverbrauch = Last − Leerlauf, **+10 %** Netzteilverluste, wegen Arbeitsspeicher (misst `powermetrics`
nicht) leicht aufrunden. Ergebnis als `watts`, Datum und Methode als `note` in die `config.toml`.
Bei geänderten Threads neu messen (wirkt ab dann).

### Referenzwerte (11/2026, XMRig 6.26.0, macOS, ohne Huge Pages)

| Gerät | Threads | Hashrate | Mehrverbrauch (powermetrics) | Bemerkung |
|---|---|---|---|---|
| MacBook Pro M3 Pro (11 Kerne) | 11 | ≈ 3.700–3.800 H/s | ≈ 10 W (+10 % → 12 W angesetzt) | kein Drosseln, ≈ 367 H/W |
| MacBook Pro M3 Pro | 6 | ≈ 2.780 H/s | ≈ 9,7 W | weniger effizient |
| MacBook Air M1 (lüfterlos) | 4 | ≈ 1.730 → 1.400 H/s | ≈ 9 W (→ 11 W angesetzt) | drosselt nach ~5 Min. |

Messwerte für ein anderes Gerät? Gern per Issue („Device measurement“) teilen – siehe
[CONTRIBUTING](../../CONTRIBUTING.de.md).

## 4. Minen

Erst wenn der Node synchron ist und P2Pool „healthy“ meldet:

```bash
deploy/mac/xmrig-start.sh        # alle Kerne
deploy/mac/xmrig-start.sh 3      # 3 Threads
```

Beim ersten Start fragt macOS nach eingehenden Verbindungen für `xmrig` → **Erlauben** (XMRig-API für den
Ledger). Test von der NAS aus:

```bash
curl -s -H "Authorization: Bearer <token>" http://<IP-DES-RECHNERS>:18000/2/summary | head -c 200
```

Hinweise:
- Nur am Netzteil (`--pause-on-battery`); bei Laptops Ladegrenze ~80 % (z. B. AlDente), harte Unterlage.
- `MEMORY 98 %` in der XMRig-Ausgabe ist macOS-Cache; maßgeblich ist der Speicherdruck in der Aktivitätsanzeige.
- „huge pages unavailable“ ist unter macOS normal.
- Windows: Smart App Control blockiert XMRig ohne Ausnahmemöglichkeit; ggf. WSL2 nutzen.

## 5. Mining-Wallet

```bash
brew install monero
mkdir -p ~/Monero/wallet
monero-wallet-cli --offline --generate-new-wallet ~/Monero/wallet/mining
```

- Seed-Wörter auf Papier (Sprache Englisch für beste Kompatibilität), nie digital speichern.
- `set setup-background-mining 0` – sonst würde die Wallet den Node solo minen lassen.
- `address` zeigt die Hauptadresse (`4…`) für `.env`; `viewkey` den View-Key (secret) für den Ledger.

Kontostand und Überweisungen gegen den eigenen Node:

```bash
monero-wallet-cli --wallet-file ~/Monero/wallet/mining --daemon-address <NAS-IP>:18089 --trusted-daemon
```

Wichtige Befehle: `refresh`, `balance`, `show_transfers`, `transfer <adresse> <betrag>`, `sweep_all <adresse>`,
`export_transfers in output=<datei.csv>`. Gemintes XMR ist ~2 Stunden gesperrt (60 Blöcke).
Jede Überweisung danach im Ledger unter „Abgänge“ eintragen.
