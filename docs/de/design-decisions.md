# Designentscheidungen

🌐 **Deutsch** · [English](../en/design-decisions.md) · [Français](../fr/design-decisions.md) · [Español](../es/design-decisions.md)

Warum Moneta so gebaut ist. Neue Einträge oben anfügen (Datum, Kontext, Entscheidung, Folgen).
Diese deutsche Fassung ist die Referenz; Übersetzungen bitte mitziehen.

### D-10 · 14.11.2026 – Neue Rechner per Code koppeln, Freigabe im Dashboard
Neue Rechner sollen ohne Handarbeit in der `config.toml` dazukommen. Der Ledger ist dafür die Leitstelle: Er
antwortet ohne Passwort auf `GET /api/moneta` (nur Dienst, Version, Stratum-Adresse), damit Installer und App ihn
im Heimnetz finden; Bonjour/mDNS scheidet aus, weil der Container im Bridge-Netz kein Multicast kann. Gekoppelt
wird mit einem 6-stelligen Code aus dem Dashboard (10 Minuten, einmalig, ungültig nach fünf Fehlversuchen) über
`POST /api/pair`. Weil das kein Browser-Formular ist, ersetzen dort Code, reines JSON und ein Größenlimit die
Same-Origin-Prüfung; `/api/heartbeat` prüft das Geräte-Token. Ein gekoppelter Rechner wird erst nach der Freigabe
mit gemessenem Mehrverbrauch abgefragt – sonst könnte jedes Gerät im LAN Stromkosten in die steuerlich relevanten
Daten schreiben. Watt liegen als Historie mit `valid_from` in der Datenbank und werden nie überschrieben; `[[miner]]`
in der `config.toml` bleibt möglich.

### D-09 · 13.11.2026 – Miner-Start per Menüleisten-App, lokal gebaut statt signiert verteilt
Rechner sollen sich ohne Terminal-Kenntnisse einrichten und per Knopf starten lassen. Ein Installer
(`deploy/mac/install.sh`) richtet XMRig als launchd-Agent ein und baut die Menüleisten-App aus dem Quellcode auf
dem Rechner selbst (`swiftc` aus den Command Line Tools, die Homebrew ohnehin braucht). Lokal gebaute Programme
tragen kein Quarantäne-Attribut; Gatekeeper fragt deshalb nicht nach, und es braucht weder ein kostenpflichtiges
Apple-Entwicklerkonto noch eine Notarisierung. XMRig wird nicht mitgeliefert, sondern über Homebrew installiert
(DONATE 0 %, eigene Updates); die App steuert nur den Agent und liest die lokale XMRig-API. Der `[[miner]]`-Eintrag
in der `config.toml` bleibt bewusst ein manueller Schritt: Die Watt werden je Erfassung festgeschrieben und müssen
vorher gemessen sein. Eine signierte, notarisierte App zum Herunterladen bleibt eine Option für später.

### D-08 · 13.11.2026 – Mehrsprachig und offen für Mitwirkende
Moneta soll über den deutschsprachigen Raum hinaus nutzbar sein und zum Mitmachen einladen. Projektsprache der
Community-Dateien (README, CONTRIBUTING, CHANGELOG, SECURITY, Vorlagen) ist Englisch; README, CONTRIBUTING und
Verhaltenskodex gibt es zusätzlich auf Deutsch, Französisch und Spanisch. Die Doku liegt unter
`docs/<de|en|fr|es>/` mit gleichen Dateinamen; bei Abweichungen gilt die deutsche Fassung – insbesondere für die
steuerliche Methodik, die deutsches Recht beschreibt. Dashboard und Excel-Bericht bleiben vorerst deutsch; ihre
Übersetzung steht oben auf der [Roadmap](../../ROADMAP.md). Verhaltenskodex: Contributor Covenant 3.0.

### D-07 · 13.11.2026 – Veröffentlichung unter EUPL-1.2
Copyleft, das auch den Betrieb als Webdienst erfasst; amtliche Fassungen in allen EU-Sprachen; Haftung und
Rechtswahl nach EU-Recht. Fremdlizenzen in [`THIRD_PARTY.md`](../../THIRD_PARTY.md), Monero-Lizenz im Image.

### D-06 · 13.11.2026 – Image über GitHub Actions, Version auf dem Server bewusst festgelegt
GitHub Actions testet und baut `ghcr.io/nexovaanalytics-oss/xmr-ledger`. Auf dem Server steht die Version fest
in `.env` (`LEDGER_VERSION`), kein Auto-Update. Jeder Excel-Bericht nennt die erzeugende Version.

### D-05 · 13.11.2026 – Kurse lokal aus 5-Minuten-Historie
Abfragen „Kurs um Zeitpunkt X“ würden dem Kursanbieter die Auszahlungszeitpunkte verraten; zusammen mit der
öffentlichen P2Pool-Adresse wäre die IP der Mining-Adresse zuordenbar. Daher werden in festem Abstand (derzeit alle
10 Minuten) die letzten 24 h geladen und lokal gespeichert; die Zuordnung erfolgt lokal (max. 15 Min. Abstand). Tageskurs nur
als Rückfall – übermittelt wird dann nur das Datum.

### D-04 · 11.11.2026 – Stromkosten = gemessener Mehrverbrauch × protokollierte Mining-Zeit
Eine Steckdosenmessung erfasst bei Laptops auch Laden und normale Nutzung. Deshalb wird der Mehrverbrauch
einmalig gemessen (Last − Leerlauf, +10 % Netzteil) und die Laufzeit automatisch über die XMRig-API erfasst.
Watt und Tarif werden je Erfassung festgeschrieben; Konfigurationsänderungen wirken nur für die Zukunft.

### D-03 · 11.11.2026 – Nur-Lesen-Wallet, Abgänge von Hand
Der Spend-Key soll nicht auf den Server. `monero-wallet-rpc` arbeitet mit Adresse + View-Key. Eine solche
Wallet sieht Eingänge, aber keine Ausgänge: Nur Coinbase-Eingänge zählen als Mining-Zufluss, sonstige Eingänge
(z. B. Rückgeld) werden separat gelistet, Abgänge im Dashboard erfasst.

### D-02 · 11.11.2026 – Lose je Auszahlung, FIFO
Jede Auszahlung ist ein Anschaffungsvorgang (AK = Wert beim Zufluss); Verbrauchsfolge FIFO; „steuerfrei ab“ =
Tag nach Ablauf der Jahresfrist (§§ 187 Abs. 1, 188 Abs. 2 BGB). Details: [Steuerliche Methodik](tax-methodology.md).

### D-01 · 11.11.2026 – Eigener Node + P2Pool auf der NAS, Rechner rechnen nur
Node und Pool brauchen Speicher, aber kaum Rechenleistung – die NAS läuft ohnehin. monerod pruned mit
`--sync-pruned-blocks`, P2Pool mini mit `--light-mode`. Die Rechner verbinden sich nur per Stratum; beliebig
viele weitere Rechner können mitminen.
