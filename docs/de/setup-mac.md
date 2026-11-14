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
- installiert bei Bedarf Homebrew und XMRig (Homebrew-Build; die Spende an die XMRig-Entwickler beträgt wie bei
  allen offiziellen Builds mindestens 1 %, `--donate-level 0` wird ignoriert);
- **sucht den XMR-Ledger im Heimnetz** (alle Adressen des eigenen /24-Netzes auf Port 8090, `GET /api/moneta`)
  und übernimmt daraus die Pool-Adresse. Wird keiner gefunden, fragt er die Pool-Adresse wie bisher ab
  (oder `LEDGER=http://<NAS-IP>:8090` angeben);
- legt das API-Token an – oder übernimmt ein Token, das für diesen Rechner schon in der `config.toml` steht;
- **schlägt die Thread-Zahl vor**: aus der Profiltabelle [`deploy/mac/profile.tsv`](../../deploy/mac/profile.tsv)
  (gemessene Geräte) oder nach Faustregel – lüfterlos (MacBook Air): Performance-Kerne − 1, mit Lüfter: alle
  Kerne. Auf Wunsch misst er gleich ein (siehe Abschnitt 3);
- kopiert die Skripte nach `~/Library/Application Support/Moneta/` und legt den launchd-Agent `moneta.xmrig` an
  (Log `~/Library/Logs/Moneta/xmrig.log`, Neustart nach einem Absturz, Autostart beim Anmelden wahlweise);
- baut die Menüleisten-App mit `swiftc` aus den Command Line Tools nach `~/Applications/Moneta Miner.app` und
  startet sie beim Anmelden. Weil sie auf dem Rechner selbst gebaut wird, braucht sie weder ein
  Apple-Entwicklerkonto noch eine Gatekeeper-Freigabe;
- gibt bei eingeschalteter macOS-Firewall `xmrig` für eingehende Verbindungen frei (zwei `sudo`-Befehle, nach
  Rückfrage). Nach `brew upgrade xmrig` den Installer erneut ausführen – die Freigabe hängt am Programmpfad;
- **koppelt den Rechner mit dem Ledger**: Im Dashboard unter **Geräte** einen Kopplungscode erzeugen und im
  Installer eingeben. Der Rechner meldet Name, Adresse, Token, Geräteprofil und – falls eingemessen – Threads und
  Mehrverbrauch. Ohne Ledger oder Code gibt er wie bisher einen `[[miner]]`-Block aus
  (`~/.config/moneta/ledger-miner.toml`).

Danach: Im Dashboard unter **Geräte** den Rechner mit gemessenem Mehrverbrauch **freigeben** (aus der
Einmessung vorausgefüllt) und in der Menüleiste **Miner starten**. Erst ab der Freigabe erfasst der Ledger den
Rechner; die Watt werden je Erfassung festgeschrieben. Eine feste IP im Router ist weiter empfehlenswert, aber
nicht mehr nötig: Bei jedem Start meldet sich der Rechner beim Ledger (`moneta-miner.sh heartbeat`), und eine
geänderte IP wird übernommen.

Ohne Rückfragen (z. B. für mehrere Rechner): `LEDGER=http://<NAS-IP>:8090 CODE=<Code> THREADS=3 MEASURE=n
AUTOSTART=n FIREWALL=j START=n ~/Moneta/deploy/mac/install.sh`. Entfernen: `~/Moneta/deploy/mac/install.sh
--uninstall` (Einstellungen, Log und XMRig bleiben).

## 1. XMRig installieren

```bash
# Homebrew, falls `brew` fehlt
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

brew install xmrig          # Homebrew-Build; DONATE 1 % (Upstream-Minimum)
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

**Automatisch:** `deploy/mac/einmessen.sh` (vom Installer angeboten, danach auch unter
`~/Library/Application Support/Moneta/einmessen.sh`) misst den Leerlauf und für zwei Thread-Zahlen – lüfterlos
Performance-Kerne − 1 und alle Performance-Kerne, mit Lüfter alle Kerne und die Performance-Kerne – Hashrate und
Leistung, jeweils nach dem Aufwärmen (lüfterlos 5 Min., damit die Drosselung erfasst wird). Vorschlag ist die
beste Hashrate je Watt; Mehrverbrauch = (Last − Leerlauf) × 1,1, aufgerundet, mit fertiger Notiz. Dauer mit
Lüfter ≈ 10 Min., lüfterlos ≈ 25 Min.; Netzteil anschließen, Mac währenddessen nicht benutzen, `sudo` für
`powermetrics`. Eigene Kandidaten: `einmessen.sh 3 4`. Die Messung mint bereits über P2Pool. Das Ergebnis
(`~/.config/moneta/einmessung.json`) schickt die Kopplung als Vorschlag mit.

**Von Hand:**

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

### Richtwerte

Hashrate und Mehrverbrauch hängen von Chip, Kühlung und Thread-Zahl ab. Faustregeln: Macs mit Lüfter laufen mit
allen Kernen ohne nennenswertes Drosseln. Lüfterlose Macs (MacBook Air) drosseln unter Dauerlast nach einigen
Minuten; dort bringen Performance-Kerne − 1 meist die bessere Hashrate je Watt. Die Werte für das eigene Gerät
liefert `einmessen.sh`, Thread-Empfehlungen je Chip stehen in
[`deploy/mac/profile.tsv`](../../deploy/mac/profile.tsv).

Messwerte für ein anderes Gerät? Gern per Issue („Device measurement“) teilen – siehe
[CONTRIBUTING](../../CONTRIBUTING.de.md).

## 4. Minen

Erst wenn der Node synchron ist und P2Pool „healthy“ meldet:

Mit dem Installer eingerichtet: Menüleiste → **Moneta Miner** → *Miner starten* / *Miner stoppen*; dort auch
Threads, Autostart beim Anmelden, das Log und der Sprung ins Dashboard. Das Fenster der App zeigt den Betrieb
dieses Macs:

- die aktuelle Hashrate neben dem Symbol in der Menüleiste (abschaltbar),
- den Verlauf der letzten 15 Min. / 1 Std. / 6 Std. mit Zeitleiste *läuft / pausiert / gestoppt*, Ø-Hashrate
  und Pausenzeit (nur im Speicher der App; den Verlauf über Tage zeigt das Dashboard),
- die Hashrate je Thread (z. B. um schwächere Effizienzkerne zu erkennen), Pool-Ping und angenommene bzw.
  abgelehnte Stratum-Shares (nicht die Sidechain-Shares von P2Pool),
- Stromquelle, Akkustand und Wärmezustand – und bei einer Pause den **Grund**: XMRig läuft mit
  `--pause-on-battery` und pausiert, sobald macOS auf Akku läuft. Das passiert auch mit eingestecktem Netzteil,
  wenn ein Ladelimit-Werkzeug wie AlDente den Akku bis zur unteren Grenze entladen lässt; die App erkennt
  laufende Ladelimit-Apps und ein angeschlossenes Netzteil und nennt das. Hinweise gibt es außerdem bei
  Energiesparmodus und Wärmedrosselung.

Der Knopf *Dashboard* öffnet `http://<Pool-Host>:8090`; eine andere Adresse in `~/.config/moneta/dashboard`
eintragen. Aktualisieren: `git pull`, dann `deploy/mac/install.sh` erneut ausführen (Einstellungen bleiben).

Dasselbe im Terminal:

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
