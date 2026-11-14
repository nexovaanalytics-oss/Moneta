# Betrieb

🌐 **Deutsch** · [English](../en/operations.md) · [Français](../fr/operations.md) · [Español](../es/operations.md)

Alle NAS-Befehle per SSH im Projektordner (Beispiel: `/volume1/docker/monero`), immer mit demselben Projektnamen
(`-p monero-pool` – ggf. an den Namen im Container Manager anpassen).

## Spickzettel

```bash
sudo docker ps --format "table {{.Names}}\t{{.Status}}"   # Übersicht
sudo docker logs --tail 5 monerod                          # Sync-Fortschritt
sudo docker exec monerod monerod status                    # Höhe, Peers, Hashrate
sudo docker attach p2pool                                  # dann "status"; lösen mit Ctrl+P, Ctrl+Q (nicht Ctrl+C!)
sudo docker logs --tail 30 xmr-ledger                      # Ledger
sudo docker logs --tail 30 wallet-rpc                      # Nur-Lesen-Wallet
sudo docker restart xmr-ledger                             # nach config.toml-Änderung
```

## Release des Ledgers

Auf dem Mac im Repo:

```bash
python -m pytest -q ledger/tests                 # muss grün sein
# CHANGELOG.md ergänzen, committen, pushen → Image :edge
git tag ledger-v1.2.0 && git push origin ledger-v1.2.0   # → Image :1.2.0
```

Alternativ im Browser: GitHub → Repository → **Releases → Draft a new release** → Tag `ledger-v1.2.0`
neu anlegen (Ziel: `main`) → Titel z. B. „Ledger 1.2.0“, Text aus `CHANGELOG.md` → **Publish release**.

GitHub → Actions → Workflow „ledger“ abwarten (Test + Image).

## Zugriff auf das Image

Das Image `ghcr.io/nexovaanalytics-oss/xmr-ledger` ist öffentlich; ein `docker login` ist nicht nötig.
Für ein privates Fork-Image: `sudo docker login ghcr.io -u <github-benutzer>` mit einem Token (classic)
mit `read:packages`.

## Neue Ledger-Version auf der NAS einspielen

**Mit dem Update-Skript** (empfohlen): Es fragt GitHub nach der neuesten Version `ledger-vX.Y.Z`, zeigt die
Änderung und fragt nach. Dann zieht es das Image (vorher wird nichts geändert), sichert die Datenbank im laufenden
Container (`ledger/data/ledger-vor-X.Y.Z-<Zeit>.sqlite`, SQLite-Backup inkl. WAL), setzt `LEDGER_VERSION` in `.env`,
startet `wallet-rpc` und `ledger` neu, zeigt das Log und den Weg zurück. Die Version bleibt fest eingetragen – das
Skript läuft nur, wenn du es startest. Einmalig herunterladen (vorher lesen):

```bash
cd /volume1/docker/monero
sudo curl -fsSLo update-ledger.sh https://raw.githubusercontent.com/nexovaanalytics-oss/Moneta/main/deploy/nas/update-ledger.sh
cat update-ledger.sh
```

Danach je Update:

```bash
cd /volume1/docker/monero
sudo bash update-ledger.sh --check     # nur anzeigen: eingetragen vs. neueste Version
sudo bash update-ledger.sh             # neueste Version, mit Rückfrage
sudo bash update-ledger.sh 1.2.0       # bestimmte Version
```

Die einzige externe Anfrage geht an `api.github.com` (Liste der Releases) – zu einem Zeitpunkt, den du wählst, ohne
Bezug zu Auszahlungen.

**Von Hand:**

```bash
cd /volume1/docker/monero
sudo sed -i 's/^LEDGER_VERSION=.*/LEDGER_VERSION=1.2.0/' .env
sudo docker compose -p monero-pool pull wallet-rpc ledger
sudo docker compose -p monero-pool up -d wallet-rpc ledger
sudo docker logs --tail 10 xmr-ledger            # Startzeile zeigt Version und DB-Schema
```

Zurück auf die alte Version: `LEDGER_VERSION` zurücksetzen, `up -d` erneut. Achtung: Datenbank-Migrationen
sind nur vorwärts gedacht – vor größeren Updates `ledger/data/` sichern.

## Monero- und P2Pool-Updates

- **monerod/p2pool:** `sudo docker compose -p monero-pool pull monerod p2pool && sudo docker compose -p monero-pool up -d`.
  Vor Hardforks Pflicht (Ankündigungen auf getmonero.org und im P2Pool-Repo).
- **wallet-rpc im Ledger-Image:** `ARG MONERO_VERSION` im `ledger/Dockerfile` erhöhen, neues Ledger-Release.
  Der Build bricht ab, wenn die Version nicht in getmonero.org/downloads/hashes.txt steht.

## Sicherung

- `ledger/data/` (Datenbank, `config.toml`, `kurse_manuell.csv`) und `.env` in Hyper Backup aufnehmen.
- `ledger/wallets/` muss nicht gesichert werden (aus View-Key neu erzeugbar).
- Blockchain-Volume nicht sichern (neu synchronisierbar).
- Seed-Wörter der Mining-Wallet: nur auf Papier.

## Fehlersuche

| Symptom | Ursache / Lösung |
|---|---|
| Ledger: „Wallet-Sync fehlgeschlagen: … refused“ | wallet-rpc startet noch; nach 2 Min. erneut prüfen |
| Ledger: Wallet-Sync-Fehler bis zum Node-Sync | normal, solange monerod synchronisiert |
| Gerät „nicht erreichbar“ | XMRig läuft nicht mit `--http-host 0.0.0.0`, Mac schläft, macOS-Firewall, falsche IP |
| Log: „XMRig-API lehnt das Token ab“ | Token in `config.toml` ≠ Token-Datei auf dem Mac |
| Gerät „pausiert“ | XMRig erreichbar, aber ohne Hashrate (Pool nicht erreichbar, Akku, pausiert) – kostet nichts |
| Zufluss „Kurs fehlt“ | wird beim nächsten Kursabruf nachgeholt; sonst `kurse_manuell.csv` |
| p2pool „unhealthy“ | Node noch nicht synchron, oder ZMQ-Port passt nicht (18084) |
| Zwei Compose-Dateien-Warnung | nur `compose.yaml` behalten |
