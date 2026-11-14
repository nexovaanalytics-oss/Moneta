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
| `[pool]` | für neue Rechner: `stratum_host` (leer = IP der NAS), `stratum_port` (Standard 3333); `pairing` (Standard `true`) erlaubt die Kopplung per Code |
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
| Zuflüsse | alle Auszahlungen mit Kurs und Kursquelle; sonstige Zugänge separat |
| Strom | Mining-Stunden, Ø Watt, kWh, Ø ct/kWh, Kosten je Gerät und Monat, dazu Summen über alle Geräte (Jahr und je Monat) |
| Auswertung | frei wählbarer Zeitraum (Vorlagen: letzte Nacht, 24 h, 7/30 Tage, Monat, Jahr): je Gerät Zeit mint/pausiert/nicht erreichbar mit Zeitleiste, Ø/Max-Hashrate, Hashes, kWh, Kosten; rechnerischer Gegenwert (Hashes ÷ Difficulty × Blockbelohnung) gegen tatsächliche Auszahlungen; je Tag; CSV |
| Lose | FIFO-Lose mit Anschaffungskosten und „steuerfrei ab“ |
| Abgänge | Überweisungen aus der Mining-Wallet erfassen/löschen |
| Verkaufs-Rechner | geplanten Verkauf/Tausch simulieren (nichts wird gespeichert) |
| Geräte | neue Rechner per Code koppeln und freigeben, Mehrverbrauch „ab jetzt“ ändern (Historie), stilllegen |

`/health` antwortet ohne Passwort mit `ok` (Docker-Healthcheck).

`/api/moneta` antwortet ebenfalls ohne Passwort, aber nur mit Dienstname, Version, Stratum-Adresse und ob
Kopplung möglich ist – daran erkennen neue Rechner den Ledger im Heimnetz. `/api/pair` (Kopplungscode) und
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
| `network.py` | Difficulty und Blockbelohnung vom eigenen Node |
| `ledger.py` | Lose, FIFO, Fristen, Jahresübersicht, Verkaufs-Rechner |
| `report.py` | Excel- und CSV-Export |
| `web.py` | Dashboard, Formulare, Downloads, Auth, CSRF-Schutz |
| `version.py` | Versionsangabe aus Build-Args |

Tests: `python -m pytest -q ledger/tests` (Fake-Wallet, Fake-XMRig, Fake-Kurse – kein Internet nötig).

## Grenzen

- Auswertung: Minutenwerte (mit Zeitleiste) bleiben 30 Tage, danach Stundenwerte. Hashes = gemeldete Hashrate ×
  Abfrageintervall (Näherung); der Gegenwert berücksichtigt keine Uncles/Orphans. Reine Anzeige, keine Steuergrundlage.
- CoinGecko (kostenlos, ohne Gewähr); historische Kurse über die freie API nur etwa ein Jahr zurück.
- Mining-Zeit zählt nur, solange der Ledger läuft und den Mac erreicht (eher zu niedrige als zu hohe Kosten).
- Netzwerkgebühren werden im Verkaufs-Rechner nicht abgezogen.
- Dashboard per HTTP: Passwort im LAN unverschlüsselt (HTTPS über Reverse-Proxy steht auf der [Roadmap](../../ROADMAP.md)).
- Oberfläche und Excel-Bericht sind derzeit nur auf Deutsch (Übersetzung steht auf der Roadmap).
- Die Steuerlogik setzt **deutsches** Recht um (siehe [Steuerliche Methodik](tax-methodology.md)); Profile für
  andere Länder stehen auf der Roadmap.
- Kopplung: Token und Geräteangaben gehen wie das Dashboard-Passwort unverschlüsselt durchs LAN. Ohne gültigen
  Code kann sich kein Rechner anmelden, und ohne Freigabe wird keiner erfasst.
