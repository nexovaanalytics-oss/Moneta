# XMR-Ledger

🌐 **Deutsch** · [English](../en/ledger.md) · [Français](../fr/ledger.md) · [Español](../es/ledger.md)

Dokumentiert das Monero-Mining automatisch: Zuflüsse mit Kurs, Stromkosten, Lose nach FIFO,
Haltefristen; dazu Dashboard, Excel-Jahresbericht und Verkaufs-Rechner.
Methodik und Normen: [Steuerliche Methodik](tax-methodology.md).

## Konfiguration

`ledger/data/config.toml` auf der NAS (Vorlage: [`ledger/config.example.toml`](../../ledger/config.example.toml)).
Enthält den **View-Key** – nicht weitergeben, nicht ins Repository.

| Abschnitt | Felder |
|---|---|
| `[wallet]` | `address` (4…), `view_key` (`viewkey` → secret), `restore_height` (Blockhöhe kurz vor Anlage der Wallet), `wallet_password` (frei) |
| `[web]` | `port`, `user`, `password` (Pflicht) |
| `[prices]` | `coingecko_api_key` (optional, kostenloser Demo-Key erhöht das Limit) |
| `[node]` | `rpc_url` des eigenen Nodes für Difficulty und Blockbelohnung (Standard `http://monerod:18089/json_rpc`, leer = aus) |
| `[pool]` | für neue Rechner: `stratum_host` (leer = IP der NAS), `stratum_port` (Standard 3333); `pairing` (Standard `true`) erlaubt die Kopplung per Code; `log` (P2Pool-Log, Standard `/p2pool/p2pool.log`) und `sidechain` (`mini`, `nano`, `main`) für [Auszahlung → Rechner](#auszahlung--rechner) |
| `[power]` | `poll_seconds`, `nas_extra_watts` (0 = NAS nicht ansetzen), `[[power.tariff]]` mit `valid_from`, `ct_per_kwh` |
| `[[miner]]` | optional statt der Kopplung im Dashboard: je Rechner `name`, `url` (`http://IP:18000`), `token`, `watts` (Mehrverbrauch), `note` (Messung) |

Prüfen vor dem Übertragen:

```bash
python3 -c "import tomllib; c=tomllib.load(open('config.toml','rb')); print(len(c['wallet']['address']), len(c['miner']))"
```

Nach Änderungen: `sudo docker restart xmr-ledger`.

## Dashboard

`http://<NAS-IP>:8090` (Basic Auth, nur LAN).

| Seite | Inhalt |
|---|---|
| Übersicht | Bestand, steuerfrei veräußerbar, Einnahmen/Strom/Ergebnis des Jahres, Gerätestatus mit Gesamtzeile (Hashrate und Mehrverbrauch aller minenden Geräte, ggf. inkl. NAS), letzte Auszahlungen, Downloads |
| Zuflüsse | alle Auszahlungen mit Kurs, Kursquelle und „Verursacht von“ (Anteile je Rechner), Tabelle „Je Rechner“ fürs Jahr; sonstige Zugänge separat |
| Strom | Mining-Stunden, Ø Watt, kWh, Ø ct/kWh, Kosten je Gerät und Monat, dazu Summen über alle Geräte (Jahr und je Monat) |
| Auswertung | frei wählbarer Zeitraum (Vorlagen: letzte Nacht, 24 h, 7/30 Tage, Monat, Jahr): je Gerät Zeit mint/pausiert/nicht erreichbar mit Zeitleiste, Ø/Max-Hashrate, Hashes, kWh, Kosten, Shares und zugeordnete XMR; rechnerischer Gegenwert (Hashes ÷ Difficulty × Blockbelohnung) gegen tatsächliche Auszahlungen; Zeitleiste „Shares und Auszahlungen“ mit „Verursacht von“; je Tag; CSV |
| Lose | FIFO-Lose mit Anschaffungskosten und „steuerfrei ab“ |
| Abgänge | Überweisungen aus der Mining-Wallet erfassen/löschen |
| Verkaufs-Rechner | geplanten Verkauf/Tausch simulieren (nichts wird gespeichert) |
| Geräte | neue Rechner per Code koppeln und freigeben, Mehrverbrauch „ab jetzt“ ändern (Historie), stilllegen |

`/health` antwortet ohne Passwort mit `ok` (Docker-Healthcheck).

`/api/moneta` antwortet ebenfalls ohne Passwort, aber nur mit Dienstname, Version, Stratum-Adresse und ob
Kopplung möglich ist – daran erkennen neue Rechner den Ledger im Heimnetz. Dazu kommen unter `economics` die
Kennzahlen für die Thread-Wahl beim Einmessen: Difficulty und Blockbelohnung vom eigenen Node, der jüngste lokale
Kurs (höchstens 2 Stunden alt) und der aktuelle Tarif, daraus Ertrag je H/s und Stromkosten je Watt und Tag
(`null`, solange Node-Wert oder Kurs fehlen). `/api/pair` (Kopplungscode) und
`/api/heartbeat` (Geräte-Token) nehmen nur JSON von Rechnern an, siehe [Rechner koppeln](#rechner-koppeln).

**Aktualisierung:** Die Übersicht holt bei geöffnetem Tab alle 30 s neue Werte, ohne die Seite neu zu laden
(`/api/live`, JSON, gleiche Anmeldung; pausiert im Hintergrund-Tab). Oben neben dem Jahr steht, wie alt der
letzte Abruf ist, bzw. „Verbindung verloren“. Ohne JavaScript lädt die Übersicht alle 2 Minuten neu. Die Daten
selbst holt der Ledger im Hintergrund: Rechner alle `poll_seconds` (Standard 60 s), Wallet alle 120 s,
Kurshistorie alle 10 Minuten.

## Rechner koppeln

Neue Rechner lassen sich ohne Eintrag in der `config.toml` anmelden:

1. Dashboard → **Geräte** → „Neuen Rechner koppeln – Code erzeugen“. Der 6-stellige Code gilt 10 Minuten und
   nur einmal; nach fünf Fehlversuchen ist er ungültig.
2. Der Rechner meldet sich mit dem Code über `POST /api/pair`: Name, XMRig-URL (nur Adressen im Heimnetz),
   API-Token, Geräteprofil (Modell, Kerne) und – falls eingemessen – Vorschlag für Threads und Mehrverbrauch.
   Installer und Menüleisten-App übernehmen das mit dem nächsten Update von `deploy/mac`.
3. Der Rechner steht unter **Wartet auf Freigabe**. Mehrverbrauch und Messnotiz prüfen bzw. eintragen,
   **Freigeben**. Erst ab dann wird er abgefragt; der Wert wird – wie bei `[[miner]]` – je Abfrage festgeschrieben.
4. Ändert sich der Mehrverbrauch (z. B. andere Thread-Zahl), unter **Aktive Rechner** einen neuen Wert speichern:
   Er gilt ab dem Speichern, frühere Erfassungen bleiben unverändert. Der Excel-Bericht (Blatt „Geräte“) zeigt
   die Historie mit „gültig ab“. **Stilllegen** beendet die Abfrage; Historie und Name bleiben sichtbar.

Gekoppelte Rechner melden sich mit ihrem Token über `POST /api/heartbeat`; eine geänderte IP wird übernommen.
Rechner aus `[[miner]]` laufen unverändert weiter (Änderungen dort wie bisher mit Neustart des Containers).

## Auszahlung → Rechner

P2Pool zahlt nach PPLNS: Eine Auszahlung verteilt sich auf alle Shares im Fenster der letzten 2160
Sidechain-Blöcke (mini ≈ 6 h, nano ≈ 18 h), gewichtet nach Share-Difficulty. Der Ledger zeigt deshalb je
Auszahlung, welche eigenen Rechner mit welchem Anteil beteiligt waren – unter **Zuflüsse** („Verursacht von“,
Tabelle „Je Rechner“) und unter **Auswertung** (Zeitleiste „Shares und Auszahlungen“, Spalten „Shares“ und
„zugeordnet XMR“).

- **exakt:** aus dem P2Pool-Log. Jede eigene Share steht dort mit Zeit, Difficulty und Client-Adresse
  (`SHARE FOUND: … client <IP:Port>[, user <Name>]`), jede Auszahlung mit Blockhöhe. Der Ledger liest das Log alle
  60 s fortlaufend ein (Tabellen `p2pool_shares`, `p2pool_payouts`). Den Rechner einer Share erkennt der Ledger am
  XMRig-Login: Der Installer aus `deploy/mac` richtet XMRig mit dem Gerätenamen als Login ein
  (`-u <Name>`, gespeichert in `~/.config/moneta/name`, bei gekoppelten Rechnern vom Ledger übernommen). Sonst
  gilt die Client-IP aus `[[miner]]` bzw. der Kopplung.
- **eindeutig:** Login `x` und eine Adresse, die keinem Rechner gehört – typisch, wenn P2Pool im Docker-Netz nur
  die Gateway-Adresse sieht. Dann entscheiden die Mining-Zeiten des Ledgers: Minte zum Zeitpunkt der Share (± zwei
  Abfragen, nach 30 Tagen auf Stundenbasis) nur ein Rechner, gehört sie ihm. Das Ergebnis wird je Share
  gespeichert. Voraussetzung: Alle Rechner am Pool sind im Ledger erfasst.
- **teilweise:** Das Log beginnt erst innerhalb des Fensters dieser Auszahlung.
- **geschätzt:** Minten zum Zeitpunkt einer Share mehrere Rechner, wird sie nach deren Hashrate in diesem Moment
  aufgeteilt (im Diagramm hohle Raute). Ohne Shares aus dem Log (Log fehlt oder beginnt später) wird nach dem
  Hash-Anteil im ganzen Fenster aufgeteilt. Kein Rechner minte laut Ledger: „unbekannt“.

**Einbinden:** Der Dienst `ledger` bekommt das P2Pool-Volume nur lesend (`deploy/nas/compose.yaml`):

```yaml
    volumes:
      - ./ledger/data:/data
      - p2pool-data:/p2pool:ro
```

Danach die `compose.yaml` auf der NAS ersetzen und `sudo docker compose -p monero-pool up -d` ausführen. Ohne das
Volume läuft alles wie bisher, nur „geschätzt“. **Bisheriger Verlauf:** P2Pool rotiert sein Log nicht selbst;
solange `p2pool.log` nicht gelöscht wurde, liest der Ledger beim ersten Start die ganze Historie ein und ordnet
auch ältere Auszahlungen exakt zu.

Reine Anzeige: Zuflüsse, Kurse, Bericht und steuerliche Behandlung bleiben unverändert; steuerlich zählt weiter
die ganze Auszahlung. Externe Dienste wie p2pool.observer werden nicht abgefragt, weil das die Mining-Adresse mit
der eigenen IP verknüpfen würde.

## Bedienung

- **Abgänge:** Die Nur-Lesen-Wallet sieht keine Ausgänge. Jede Überweisung erfassen: Menge = an andere
  gesendeter Betrag + Netzwerkgebühr (Rückgeld nicht mitzählen); Art Verkauf/Tausch, Bezahlung oder Übertrag
  auf eigene Wallet; bei Verkauf/Tausch/Bezahlung den EUR-Gegenwert.
- **Kurs fehlt/korrigieren:** `ledger/data/kurse_manuell.csv`, je Zeile `TXID;Kurs` oder `JJJJ-MM-TT;Kurs`
  (Dezimalkomma erlaubt). Gilt nur für Zuflüsse ohne gespeicherten Kurs.
- **Strompreis ändert sich:** neuen `[[power.tariff]]`-Block mit `valid_from` ergänzen, Container neu starten.
- **Jahresbericht:** Übersicht → „Excel-Bericht“ (Blätter: Übersicht mit Freigrenzen, Zuflüsse, Strom, Geräte,
  Lose, Abgänge, sonstige Zugänge). Die Übersicht nennt die erzeugende Ledger-Version.

## Aufbau des Codes (`ledger/app/`)

| Modul | Aufgabe |
|---|---|
| `main.py` | Start, Threads, Signale |
| `config.py` | `config.toml` lesen und prüfen |
| `db.py` | SQLite, Migrationen (`PRAGMA user_version`), Verbindungen je Thread |
| `walletsync.py` | wallet-rpc: Wallet anlegen/öffnen, Eingänge lesen, Reorgs bereinigen |
| `prices.py` | 5-Minuten-Kurshistorie, Kurszuordnung, Tageskurs-Rückfall, manuelle Kurse |
| `miners.py` | XMRig-API abfragen, Mining-Zeit und Kosten festschreiben |
| `devices.py` | gekoppelte Rechner: Kopplungscode, Anmeldung, Freigabe, Watt-Historie, Heartbeat |
| `activity.py` | Stundenwerte je Gerät, Auswertung über Zeiträume |
| `shares.py` | P2Pool-Log einlesen, Auszahlungen den Rechnern zuordnen (nur Anzeige) |
| `network.py` | Difficulty und Blockbelohnung vom eigenen Node |
| `ledger.py` | Lose, FIFO, Fristen, Jahresübersicht, Verkaufs-Rechner |
| `report.py` | Excel- und CSV-Export |
| `web.py` | Dashboard, Formulare, Downloads, Auth, CSRF-Schutz |
| `version.py` | Versionsangabe aus Build-Args |

Tests: `python -m pytest -q ledger/tests` (Fake-Wallet, Fake-XMRig, Fake-Kurse – kein Internet nötig).

## Grenzen

- Auswertung: Minutenwerte (mit Zeitleiste) bleiben 30 Tage, danach Stundenwerte. Hashes = gemeldete Hashrate ×
  Abfrageintervall (Näherung); der Gegenwert berücksichtigt keine Uncles/Orphans. Reine Anzeige, keine Steuergrundlage.
- Auszahlung → Rechner: Das Fenster ist zeitbasiert (2160 × Blockzeit) und damit eine Näherung an das
  PPLNS-Fenster; Uncles bleiben unberücksichtigt. P2Pool hinter dem Docker-Port-Proxy sieht nur die
  Gateway-Adresse; maßgeblich ist dann der XMRig-Login. Shares aus der Zeit davor ordnen die Mining-Zeiten zu.
- CoinGecko (kostenlos, ohne Gewähr); historische Kurse über die freie API nur etwa ein Jahr zurück.
- Mining-Zeit zählt nur, solange der Ledger läuft und den Mac erreicht (eher zu niedrige als zu hohe Kosten).
- Netzwerkgebühren werden im Verkaufs-Rechner nicht abgezogen.
- Dashboard per HTTP: Passwort im LAN unverschlüsselt (HTTPS über Reverse-Proxy steht auf der [Roadmap](../../ROADMAP.md)).
- Oberfläche und Excel-Bericht sind derzeit nur auf Deutsch (Übersetzung steht auf der Roadmap).
- Die Steuerlogik setzt **deutsches** Recht um (siehe [Steuerliche Methodik](tax-methodology.md)); Profile für
  andere Länder stehen auf der Roadmap.
- Kopplung: Token und Geräteangaben gehen wie das Dashboard-Passwort unverschlüsselt durchs LAN. Ohne gültigen
  Code kann sich kein Rechner anmelden, und ohne Freigabe wird keiner erfasst.
