# Bei Moneta mitmachen

🌐 [English](CONTRIBUTING.md) · **Deutsch** · [Français](CONTRIBUTING.fr.md) · [Español](CONTRIBUTING.es.md)

Schön, dass du helfen willst! Moneta ist ein kleines Hobbyprojekt, und jeder Beitrag zählt – ein Messwert von
deinem Gerät, eine Übersetzung, ein Fehlerbericht oder ein Pull Request. Issues und Pull Requests kannst du auf
**Deutsch, Englisch, Französisch oder Spanisch** schreiben.

Mit deiner Teilnahme akzeptierst du unseren [Verhaltenskodex](CODE_OF_CONDUCT.de.md).

## Möglichkeiten mitzumachen

| Du hast … | Du könntest … |
|---|---|
| 10 Minuten | Hashrate und Stromverbrauch deines Geräts teilen (Issue-Formular „Device measurement“) |
| eine Stunde | einen Tippfehler beheben, eine Anleitung verbessern, eine veraltete Übersetzung nachziehen |
| einen Abend | eine Anleitung schreiben (Linux, Windows/WSL2, QNAP, Unraid, TrueNAS …), ein [Good first issue](https://github.com/nexovaanalytics-oss/Moneta/labels/good%20first%20issue) übernehmen |
| mehr Zeit | Dashboard und Bericht übersetzen, ein Steuerprofil für dein Land ergänzen, das arm64-Image bauen – siehe [Roadmap](ROADMAP.md) |

Ideen und Fragen sind ebenso willkommen – als Issue oder in den Discussions.

## Bevor du loslegst

- Schau in die [Issues](https://github.com/nexovaanalytics-oss/Moneta/issues) und die [Roadmap](ROADMAP.md) –
  vielleicht arbeitet schon jemand daran.
- Bei größeren Änderungen bitte zuerst ein Issue mit deinem Plan anlegen. Das spart allen Zeit.
- Lies [Architektur](docs/de/architecture.md) und [Designentscheidungen](docs/de/design-decisions.md), um zu
  verstehen, warum Dinge so gebaut sind.

## Entwicklungsumgebung

```bash
git clone https://github.com/<dein-konto>/Moneta.git
cd Moneta
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r ledger/requirements.txt pytest
python -m pytest -q ledger/tests              # läuft ohne Internet (Fake-Wallet, Fake-XMRig, Fake-Kurse)
docker build -f ledger/Dockerfile .           # Build-Kontext ist das Repository-Wurzelverzeichnis
```

Für die Arbeit am Ledger brauchst du weder Monero-Node noch Miner – die Tests simulieren beides.

## Grundregeln

**Datenschutz zuerst – das ist ein öffentliches Repository.**
- Nie Geheimnisse committen: Seed, Passwörter, View-Key, Tokens, `config.toml`, `.env`, Datenbanken,
  Wallet-Dateien.
- Keine persönlichen Umgebungsdaten: echte IP-Adressen, Benutzernamen, Mining-Adressen, Hostnamen, eigene Server
  oder Hoster. Platzhalter verwenden, z. B. `<NAS-IP>`, `<NAS-BENUTZER>`, `4...`.
- Vor jedem Commit `git status` und `git diff --cached` prüfen.

**Code (`ledger/`)**
- Python 3.12, nur Standardbibliothek + `openpyxl` (+ `tzdata`). Neue Abhängigkeiten nur mit gutem Grund und
  Eintrag in [`THIRD_PARTY.md`](THIRD_PARTY.md).
- Neue Quelldateien beginnen mit `# SPDX-License-Identifier: EUPL-1.2`.
- **Steuerrelevante Daten sind unveränderlich:** gespeicherte Kurse, Watt, Tarife und Kosten werden nie
  nachträglich umgerechnet. Konfigurationsänderungen wirken nur für die Zukunft.
- **DB-Migrationen nur additiv:** neue Einträge ans Ende von `db.MIGRATIONS` anhängen, nie bestehende ändern.
- Beträge in Piconero (`int`), Geld als `Decimal`; EUR je Zufluss auf Cent runden, dann summieren.
- Externe Abfragen dürfen keine Rückschlüsse auf Zeitpunkte einzelner Auszahlungen erlauben.
- POST-Endpunkte nur mit Same-Origin-Prüfung; das Dashboard ist nur fürs LAN gedacht.
- `python -m pytest -q ledger/tests` muss grün sein; neue Funktionen bekommen Tests (Fake-Dienste, kein Internet).
- Kommentare auf Englisch oder Deutsch. Die Oberfläche ist derzeit deutsch – UI-Texte sollen in
  Übersetzungsdateien wandern (siehe Roadmap), daher neue UI-Texte kurz und leicht extrahierbar halten.

## Dokumentation und Übersetzungen

- Die Doku liegt unter `docs/<de|en|fr|es>/` mit **gleichen Dateinamen**; jede Seite beginnt mit einem
  Sprachumschalter.
- Deutsch ist die Referenzfassung. Wenn du eine Seite änderst, zieh die anderen Sprachen nach, wenn du kannst –
  sonst vermerke es im Pull Request, dann gleichen wir sie an (oder leg ein „Translation“-Issue an).
- Die Steuerseiten beschreiben deutsches Recht. Normen exakt angeben (§ 22 Nr. 3 EStG, § 23 EStG, BMF-Schreiben
  vom 06.03.2025); beschreiben, was das Tool rechnet – keine Steuerberatung.
- Aktuelle Zahlen (Kurse, Hashrate, Difficulty, Strompreise) immer mit Datum und Quelle.
- Eine neue Sprache ist sehr willkommen: `docs/<code>/` mit denselben Dateinamen anlegen und in
  [`docs/README.md`](docs/README.md) sowie den Sprachumschaltern ergänzen.

## Pull Requests

1. Repository forken und einen Branch anlegen (`fix/…`, `feat/…`, `docs/…`).
2. Pull Requests klein und fokussiert halten; beschreiben, *was* und *warum*.
3. Für sichtbare Änderungen einen Eintrag unter „Unreleased“ in [`CHANGELOG.md`](CHANGELOG.md) ergänzen.
4. Tests müssen grün sein, die Checkliste der Pull-Request-Vorlage vollständig.

Reviews passieren in der Freizeit – bitte ein paar Tage Geduld. Releases erstellen die Maintainer
(Tag `ledger-vX.Y.Z`, siehe [Betrieb](docs/de/operations.md)).

## Beiträge mit KI-Unterstützung

Beiträge, die mit Hilfe von KI-Werkzeugen entstanden sind, sind willkommen. Das Repository enthält eine
[`CLAUDE.md`](CLAUDE.md) mit den Projektregeln für Coding-Assistenten. Die Verantwortung bleibt bei dir: prüfen,
testen und sicherstellen, dass keine Geheimnisse oder persönlichen Daten enthalten sind.

## Sicherheit

Sicherheitslücken bitte **nicht** in öffentlichen Issues melden – siehe [SECURITY.md](SECURITY.md).

## Lizenz

Moneta steht unter der [EUPL-1.2](LICENSE). Mit dem Einreichen eines Beitrags stimmst du zu, dass er ebenfalls
unter der EUPL-1.2 lizenziert wird.
