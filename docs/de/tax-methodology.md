# Steuerliche Methodik

🌐 **Deutsch** · [English](../en/tax-methodology.md) · [Français](../fr/tax-methodology.md) · [Español](../es/tax-methodology.md)

> **Keine Steuer- oder Rechtsberatung.** Diese Seite beschreibt, wie der XMR-Ledger rechnet, und stützt sich auf
> die deutsche Verwaltungsauffassung (Stand 11/2026). Sie ersetzt keine Prüfung im Einzelfall; für andere
> Länder gelten andere Regeln. Diese deutsche Fassung ist maßgeblich.

Das Tool liefert Zahlen und Belege; die Einordnung im Einzelfall trifft der Steuerpflichtige.
Grundlage ist die Verwaltungsauffassung im BMF-Schreiben vom 06.03.2025
(IV C 1 - S 2256/00042/064/043, „Einzelfragen zur ertragsteuerrechtlichen Behandlung bestimmter Kryptowerte“,
ersetzt das Schreiben vom 10.05.2022; Blockerstellung Rn. 35 ff.).

## Zuflüsse (Einnahmen)

- Einkünfte aus der Blockerstellung sind – je nach Umständen – gewerblich (§ 15 EStG) oder sonstige Einkünfte
  aus Leistungen (§ 22 Nr. 3 EStG); das gilt auch für Kryptowerte aus Mining-Pools.
- Ansatz mit dem **Marktkurs im Zeitpunkt des Zugangs** (vereinfacht: Einbuchung in der Wallet).
- Umsetzung: Zeitpunkt = Blockzeit der Coinbase-Transaktion; Kurs = nächstgelegener CoinGecko-5-Minuten-Kurs
  (max. 15 Min. Abstand), sonst Tageskurs 00:00 UTC, sonst manuell. Quelle wird je Zufluss gespeichert.
- EUR je Zufluss auf Cent gerundet, dann summiert.
- Nur Coinbase-Eingänge zählen; sonstige Eingänge (z. B. Rückgeld eigener Überweisungen) werden gelistet,
  aber nicht als Einnahme gezählt.

## Werbungskosten / Betriebsausgaben: Strom

- Gemessener **Mehrverbrauch** je Gerät × automatisch protokollierte **Mining-Zeit** × **Strompreis**.
- Messung: `powermetrics` Last − Leerlauf, +10 % Netzteilverluste, wegen RAM aufgerundet; Datum und Methode
  stehen in `config.toml` (`note`) und im Bericht (Blatt „Geräte“).
- Watt und Tarif werden je Erfassung festgeschrieben; spätere Änderungen wirken nur für die Zukunft.
- Optional: Mehrverbrauch der NAS (`nas_extra_watts`) – derzeit 0, da die NAS ohnehin läuft.
- Nicht erfasst: Abschreibung vorhandener Hardware (Macs werden privat genutzt).

## Freigrenze § 22 Nr. 3 EStG

Der Bericht prüft, ob das Ergebnis (Einnahmen − Strom) unter **256 €** liegt. Die Freigrenze gilt für alle
Einkünfte aus Leistungen des Jahres zusammen. Verluste sind nur mit Einkünften nach § 22 Nr. 3 verrechenbar
(§ 22 Nr. 3 S. 3, 4 EStG, § 10d entsprechend). Einkünfteerzielungsabsicht bei dauerhaft negativem Ergebnis ist
gesondert zu würdigen.

## Veräußerung (§ 23 Abs. 1 S. 1 Nr. 2 EStG)

- Jede Auszahlung gilt als **Anschaffung**; Anschaffungskosten = Wert beim Zufluss.
- **Verbrauchsfolge FIFO** je Wallet (Mining-Wallet).
- **Jahresfrist:** „steuerfrei ab“ = Tag nach Ablauf eines Jahres ab Zufluss (§§ 187 Abs. 1, 188 Abs. 2 BGB;
  29.02. → 01.03.).
- Auch Tausch in andere Kryptowerte und Bezahlung mit XMR sind Veräußerungen; Erlös = EUR-Wert des Erhaltenen.
- Übertrag auf eine eigene Wallet ist keine Veräußerung; die Lose (AK, Datum) werden im Bericht ausgewiesen,
  damit sie in der Ziel-Wallet fortgeführt werden können.
- Freigrenze **1.000 €** (§ 23 Abs. 3 S. 5 EStG) für alle privaten Veräußerungsgeschäfte des Jahres.

## Belege

- Excel-Jahresbericht (inkl. erzeugender Ledger-Version), CSV der Zuflüsse.
- Wallet-Export: `export_transfers in output=…` in `monero-wallet-cli`.
- P2Pool-Nachweis: mini.p2pool.observer (Adresse eingeben).
- Herkunftsnachweis für Banken/Börsen: Mining-Adresse, Auszahlungen, Stromkosten.

## Regulatorik

Ab dem **10.07.2027** (AMLR, VO (EU) 2024/1624, Art. 79) dürfen EU-regulierte Krypto-Dienstleister keine
Konten mit Privacy-Coins wie Monero mehr führen. Halten in eigener Wallet und Mining bleiben erlaubt; ein Tausch
in Euro wäre dann nur noch zweistufig (dezentral XMR → BTC, danach regulierte Börse) möglich.

## Andere Länder

Der Ledger setzt derzeit nur deutsches Recht um. Steuerprofile für andere Länder (Haltefristen, Freigrenzen,
Verbrauchsfolgen) stehen auf der [Roadmap](../../ROADMAP.md) – Beiträge von Leuten, die die Regeln ihres Landes
kennen, sind sehr willkommen.
