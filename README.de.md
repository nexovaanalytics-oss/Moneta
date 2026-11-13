# Moneta

**Mining für MacBook mit NAS-Anbindung – präg dir dein eigenes Monero.**
Die NAS betreibt Node und P2Pool, die MacBooks rechnen – und der XMR-Ledger führt über jede Auszahlung
steuerfest Buch.

🌐 [English](README.md) · **Deutsch** · [Français](README.fr.md) · [Español](README.es.md)

[![Lizenz: EUPL-1.2](https://img.shields.io/badge/license-EUPL--1.2-blue.svg)](LICENSE)
[![ledger CI](https://github.com/nexovaanalytics-oss/Moneta/actions/workflows/ledger.yml/badge.svg)](https://github.com/nexovaanalytics-oss/Moneta/actions/workflows/ledger.yml)
[![Doku: DE · EN · FR · ES](https://img.shields.io/badge/docs-DE%20%C2%B7%20EN%20%C2%B7%20FR%20%C2%B7%20ES-informational.svg)](docs/README.md)
[![Mitmachen erwünscht](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.de.md)

> Benannt nach Juno Moneta, in deren Tempel auf dem Kapitol die römische Münzprägestätte stand –
> daher „Money“, „Münze“ und über Esperanto auch „Monero“.

```
Rechner 1 (z. B. MacBook Pro) ─┐                         NAS (z. B. Synology DS920+)
Rechner 2 (z. B. MacBook Air) ─┼── XMRig ── Stratum ──▶ p2pool (mini) ──▶ monerod (pruned) ──▶ Monero-Netz
                               │                                             ▲
                               └── XMRig-API ◀── xmr-ledger ── wallet-rpc ───┘
                                                     │  (View-Key, nur lesend)
                                                Dashboard :8090 · Excel-Jahresbericht
```

## Warum Moneta?

- **Ohne Mittelsmann.** Eigener Node plus P2Pool: kein Pool-Betreiber, kein Konto, keine Pool-Gebühr. Die
  Auszahlungen landen direkt in den Monero-Blöcken, die der Pool findet, in deiner Wallet.
- **Hardware, die du schon hast.** Eine NAS, die ohnehin läuft, und die Laptops auf deinem Schreibtisch.
- **Privatsphäre eingebaut.** Der Server bekommt nur eine Nur-Lesen-Wallet – der Spend-Key verlässt nie deinen
  Rechner. Kursabfragen verraten nicht, wann du Auszahlungen erhalten hast.
- **Bücher, die aufgehen.** Jede Auszahlung mit EUR-Kurs zum Zuflusszeitpunkt, Stromkosten aus gemessenen Watt ×
  protokollierter Mining-Zeit, FIFO-Lose mit Haltefristen und ein Excel-Jahresbericht.
- **Ehrliche Zahlen.** Bei deutschen Strompreisen ist Heim-Mining ein Hobby, keine Geldanlage – Moneta zeigt dir
  genau, was es kostet und was es bringt.

## XMR-Ledger

- **Zuflüsse** jeder P2Pool-Auszahlung über eine Nur-Lesen-Wallet (View-Key) am eigenen Node
- **Kurs zum Zuflusszeitpunkt** aus lokal gespeicherten 5-Minuten-Kursen – ohne dem Kursanbieter
  Auszahlungszeitpunkte zu verraten
- **Stromkosten** aus gemessenem Mehrverbrauch × automatisch protokollierter Mining-Zeit
- **Lose nach FIFO** mit Anschaffungskosten und „steuerfrei ab“-Datum (§ 23 EStG)
- **Dashboard**, **Excel-Jahresbericht** (inkl. Freigrenzen-Prüfung), **Verkaufs-Rechner**
- Python 3.12, nur Standardbibliothek + openpyxl; Image `ghcr.io/nexovaanalytics-oss/xmr-ledger`

## Inhalt

| Ordner | Was |
|---|---|
| [`ledger/`](ledger/) | XMR-Ledger: Python-App, Dockerfile, Tests |
| [`deploy/nas/`](deploy/nas/) | `compose.yaml` und `.env.example` für den NAS-Stack |
| [`deploy/mac/`](deploy/mac/) | Startskript für XMRig, Strommessung |
| [`docs/`](docs/README.md) | Dokumentation auf Deutsch, Englisch, Französisch und Spanisch |

## Dokumentation

- [Architektur](docs/de/architecture.md) – Komponenten, Ports, Datenflüsse
- [Setup NAS](docs/de/setup-nas.md) · [Setup Rechner (macOS)](docs/de/setup-mac.md)
- [XMR-Ledger bedienen](docs/de/ledger.md) · [Steuerliche Methodik](docs/de/tax-methodology.md)
- [Betrieb: Updates, Releases, Backup, Fehlersuche](docs/de/operations.md)
- [Designentscheidungen](docs/de/design-decisions.md)

## Schnellstart

1. Mining-Wallet anlegen, Hauptadresse und View-Key notieren ([Setup Rechner](docs/de/setup-mac.md#5-mining-wallet))
2. Auf der NAS `compose.yaml`, `.env` und `ledger/data/config.toml` anlegen, starten ([Setup NAS](docs/de/setup-nas.md))
3. Node synchronisieren lassen (mehrere Tage), dann XMRig mit `deploy/mac/xmrig-start.sh` starten
4. Dashboard unter `http://<NAS-IP>:8090`

Entwicklung: `pip install -r ledger/requirements.txt pytest && python -m pytest -q ledger/tests`

## 🤝 Mach mit!

Moneta ist als Hobbyprojekt entstanden und steht jetzt allen offen. Ob du auf einem Raspberry Pi minst, die
Steuerregeln in Österreich, der Schweiz, Frankreich oder Spanien kennst oder einfach einen Tippfehler gefunden
hast – du bist willkommen. Issues und Pull Requests gern auf **Deutsch, Englisch, Französisch oder Spanisch**.

Gute Einstiegspunkte:

- 🌍 **Dashboard und Excel-Bericht übersetzen** (EN/FR/ES und mehr)
- 🧾 **Steuerprofil für dein Land** ergänzen
- 📊 **Hashrate und Stromverbrauch** deines Geräts teilen – ein Issue-Formular, kein Code nötig
- 🐧 **Anleitungen** für Linux, Windows (WSL2) und andere NAS-Systeme
- 🧩 **arm64-Image** für Raspberry Pi und ARM-NAS

→ [Roadmap](ROADMAP.md) · [Leitfaden für Beiträge](CONTRIBUTING.de.md) ·
[Good first issues](https://github.com/nexovaanalytics-oss/Moneta/labels/good%20first%20issue) ·
[Verhaltenskodex](CODE_OF_CONDUCT.de.md)

## Wichtige Hinweise

- **Keine Steuer- oder Rechtsberatung.** Der Ledger setzt die deutsche Verwaltungsauffassung (BMF-Schreiben
  vom 06.03.2025) technisch um; die Einordnung im Einzelfall liegt bei dir bzw. deiner Beratung.
- **Keine Gewähr** für Kurse, Berechnungen und Berichte – Ergebnisse vor Verwendung prüfen.
- **Wirtschaftlichkeit:** Heim-Mining ist bei deutschen Strompreisen meist ein Hobby, keine Geldanlage.
- **Rechtslage:** Ab 10.07.2027 dürfen EU-regulierte Krypto-Dienstleister keine Privacy-Coins wie Monero mehr
  führen (AMLR). Prüfe die für dich geltenden Regeln selbst.
- **Hosting:** Viele Hoster verbieten Mining und Blockchain-Nodes – zu Hause betreiben oder AGB prüfen.
- Sicherheitslücken bitte vertraulich melden: [SECURITY.md](SECURITY.md).

## Lizenz

Copyright © 2026 Moneta-Mitwirkende.
Lizenziert unter der **European Union Public Licence v. 1.2** ([LICENSE](LICENSE), SPDX: `EUPL-1.2`).
Amtliche Fassungen in allen EU-Sprachen, auch Deutsch:
https://interoperable-europe.ec.europa.eu/collection/eupl/eupl-text-eupl-12
Fremdsoftware und Datenquellen: [THIRD_PARTY.md](THIRD_PARTY.md).
