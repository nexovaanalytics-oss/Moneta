# Setup Rechner (macOS)

🌐 **Deutsch** · [English](../en/setup-mac.md) · [Français](../fr/setup-mac.md) · [Español](../es/setup-mac.md)

Beschrieben für macOS mit Apple Silicon; unter Linux sind die Schritte analog (XMRig aus der
Paketverwaltung bzw. von xmrig.com, Strommessung z. B. mit Messsteckdose).

## Schnelleinrichtung: Installer und Menüleisten-App

Der Installer erledigt die Schritte 1, 2 und 4 und richtet XMRig als launchd-Agent mit der Menüleisten-App
**Moneta Miner** ein (macOS 13 oder neuer). Er kann gefahrlos erneut ausgeführt werden (z. B. nach `git pull`);
vorhandene Einstellungen bleiben erhalten.

```bash
git clone https://github.com/nexovaanalytics-oss/Moneta.git ~/Moneta
~/Moneta/deploy/mac/install.sh
```

Was der Installer tut:
- installiert bei Bedarf Homebrew und XMRig (Homebrew-Build, DONATE 0 %);
- fragt Pool-Adresse und Threads ab und legt das API-Token an – oder übernimmt ein Token, das für diesen Rechner
  schon in der `config.toml` steht;
- kopiert die Skripte nach `~/Library/Application Support/Moneta/` und legt den launchd-Agent `moneta.xmrig` an
  (Log `~/Library/Logs/Moneta/xmrig.log`, Neustart nach einem Absturz, Autostart beim Anmelden wahlweise);
- baut die Menüleisten-App mit `swiftc` aus den Command Line Tools nach `~/Applications/Moneta Miner.app` und
  startet sie beim Anmelden. Weil sie auf dem Rechner selbst gebaut wird, braucht sie weder ein
  Apple-Entwicklerkonto noch eine Gatekeeper-Freigabe;
- gibt bei eingeschalteter macOS-Firewall `xmrig` für eingehende Verbindungen frei (zwei `sudo`-Befehle, nach
  Rückfrage). Nach `brew upgrade xmrig` den Installer erneut ausführen – die Freigabe hängt am Programmpfad;
- gibt einen fertigen `[[miner]]`-Block für die `config.toml` des Ledgers aus (auch in
  `~/.config/moneta/ledger-miner.toml`).

Danach in dieser Reihenfolge: IP des Rechners im Router fest vergeben → Mehrverbrauch messen (Abschnitt 3) →
Block mit dem gemessenen `watts` in die `config.toml` eintragen → `sudo docker restart xmr-ledger` auf der NAS →
in der Menüleiste **Miner starten**. Die Watt werden je Erfassung festgeschrieben; ein Platzhalterwert lässt sich
später nicht korrigieren.

Ohne Rückfragen (z. B. für mehrere Rechner): `POOL=<NAS-IP>:3333 THREADS=3 AUTOSTART=n FIREWALL=j START=n
~/Moneta/deploy/mac/install.sh`. Entfernen: `~/Moneta/deploy/mac/install.sh --uninstall` (Einstellungen, Log
und XMRig bleiben).

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

Mit dem Installer eingerichtet: Menüleiste → **Moneta Miner** → *Miner starten* / *Miner stoppen*; dort auch
Threads, Autostart beim Anmelden, Hashrate, Pool-Verbindung und das Log. Dasselbe im Terminal:

```bash
MM="$HOME/Library/Application Support/Moneta/moneta-miner.sh"
"$MM" start                  # bzw. stop, restart
"$MM" status
"$MM" threads 3              # oder: all – läuft XMRig, startet er neu
"$MM" autostart on           # oder: off
"$MM" log -f
```

Ohne Installer, von Hand im Vordergrund:

```bash
deploy/mac/xmrig-start.sh        # Threads aus ~/.config/moneta/threads, sonst alle Kerne
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
