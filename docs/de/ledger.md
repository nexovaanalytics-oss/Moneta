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
| `[power]` | `poll_seconds`, `nas_extra_watts` (0 = NAS nicht ansetzen), `[[power.tariff]]` mit `valid_from`, `ct_per_kwh` |
| `[[miner]]` | je Rechner `name`, `url` (`http://IP:18000`), `token`, `watts` (Mehrverbrauch), `note` (Messung) |

Prüfen vor dem Übertragen:

```bash
python3 -c "import tomllib; c=tomllib.load(open('config.toml','rb')); print(len(c['wallet']['address']), len(c['miner']))"
```

Nach Änderungen: `sudo docker restart xmr-ledger`.

## Dashboard

`http://<NAS-IP>:8090` (Basic Auth, nur LAN).

| Seite | Inhalt |
|---|---|
| Übersicht | Bestand, steuerfrei veräußerbar, Einnahmen/Strom/Ergebnis des Jahres, Gerätestatus, letzte Auszahlungen, Downloads |
| Zuflüsse | alle Auszahlungen mit Kurs und Kursquelle; sonstige Zugänge separat |
| Strom | Mining-Stunden, Ø Watt, kWh, Ø ct/kWh, Kosten je Gerät und Monat |
| Lose | FIFO-Lose mit Anschaffungskosten und „steuerfrei ab“ |
| Abgänge | Überweisungen aus der Mining-Wallet erfassen/löschen |
| Verkaufs-Rechner | geplanten Verkauf/Tausch simulieren (nichts wird gespeichert) |

`/health` antwortet ohne Passwort mit `ok` (Docker-Healthcheck).

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
| `ledger.py` | Lose, FIFO, Fristen, Jahresübersicht, Verkaufs-Rechner |
| `report.py` | Excel- und CSV-Export |
| `web.py` | Dashboard, Formulare, Downloads, Auth, CSRF-Schutz |
| `version.py` | Versionsangabe aus Build-Args |

Tests: `python -m pytest -q ledger/tests` (Fake-Wallet, Fake-XMRig, Fake-Kurse – kein Internet nötig).

## Grenzen

- CoinGecko (kostenlos, ohne Gewähr); historische Kurse über die freie API nur etwa ein Jahr zurück.
- Mining-Zeit zählt nur, solange der Ledger läuft und den Mac erreicht (eher zu niedrige als zu hohe Kosten).
- Netzwerkgebühren werden im Verkaufs-Rechner nicht abgezogen.
- Dashboard per HTTP: Passwort im LAN unverschlüsselt (HTTPS über Reverse-Proxy steht auf der [Roadmap](../../ROADMAP.md)).
- Oberfläche und Excel-Bericht sind derzeit nur auf Deutsch (Übersetzung steht auf der Roadmap).
- Die Steuerlogik setzt **deutsches** Recht um (siehe [Steuerliche Methodik](tax-methodology.md)); Profile für
  andere Länder stehen auf der Roadmap.
