# Operations

🌐 [Deutsch](../de/operations.md) · **English** · [Français](../fr/operations.md) · [Español](../es/operations.md)

Run all NAS commands via SSH in the project folder (example: `/volume1/docker/monero`), always with the same
project name (`-p monero-pool` – adjust to the name used in Container Manager if necessary).

## Cheat sheet

```bash
sudo docker ps --format "table {{.Names}}\t{{.Status}}"   # overview
sudo docker logs --tail 5 monerod                          # sync progress
sudo docker exec monerod monerod status                    # height, peers, hashrate
sudo docker attach p2pool                                  # then "status"; detach with Ctrl+P, Ctrl+Q (not Ctrl+C!)
sudo docker logs --tail 30 xmr-ledger                      # ledger
sudo docker logs --tail 30 wallet-rpc                      # view-only wallet
sudo docker restart xmr-ledger                             # after changing config.toml
```

## Releasing the ledger

On your computer, in the repository:

```bash
python -m pytest -q ledger/tests                 # must pass
# update CHANGELOG.md, commit, push → image :edge
git tag ledger-v1.2.0 && git push origin ledger-v1.2.0   # → image :1.2.0
```

Alternatively in the browser: GitHub → repository → **Releases → Draft a new release** → create the new tag
`ledger-v1.2.0` (target: `main`) → title e.g. "Ledger 1.2.0", text from `CHANGELOG.md` → **Publish release**.

Then wait for GitHub → Actions → workflow "ledger" (tests + image).

## Image access

The image `ghcr.io/nexovaanalytics-oss/xmr-ledger` is public; no `docker login` is needed.
For an image from a private fork: `sudo docker login ghcr.io -u <github-user>` with a (classic) token that has
`read:packages`.

## Deploying a new ledger version on the NAS

```bash
cd /volume1/docker/monero
sudo sed -i 's/^LEDGER_VERSION=.*/LEDGER_VERSION=1.2.0/' .env
sudo docker compose -p monero-pool pull wallet-rpc ledger
sudo docker compose -p monero-pool up -d wallet-rpc ledger
sudo docker logs --tail 10 xmr-ledger            # start line shows version and DB schema
```

Rolling back: reset `LEDGER_VERSION`, run `up -d` again. Caution: database migrations are forward-only – back up
`ledger/data/` before larger updates.

## Monero and P2Pool updates

- **monerod/p2pool:** `sudo docker compose -p monero-pool pull monerod p2pool && sudo docker compose -p monero-pool up -d`.
  Mandatory before hard forks (announcements on getmonero.org and in the P2Pool repository).
- **wallet-rpc in the ledger image:** bump `ARG MONERO_VERSION` in `ledger/Dockerfile`, cut a new ledger release.
  The build fails if the version is not listed in getmonero.org/downloads/hashes.txt.

## Backup

- Include `ledger/data/` (database, `config.toml`, `kurse_manuell.csv`) and `.env` in your backup (e.g. Hyper Backup).
- `ledger/wallets/` does not need a backup (can be recreated from the view key).
- Do not back up the blockchain volume (can be resynced).
- Seed words of the mining wallet: on paper only.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Ledger: "Wallet-Sync fehlgeschlagen: … refused" | wallet-rpc is still starting; check again after 2 min |
| Ledger: wallet sync errors until the node is synced | normal while monerod is syncing |
| Device "nicht erreichbar" (unreachable) | XMRig not running with `--http-host 0.0.0.0`, computer asleep, macOS firewall, wrong IP |
| Log: "XMRig-API lehnt das Token ab" (token rejected) | token in `config.toml` ≠ token file on the computer |
| Device "pausiert" (paused) | XMRig reachable but no hashrate (pool unreachable, on battery, paused) – costs nothing |
| Inflow "Kurs fehlt" (price missing) | filled in on the next price fetch; otherwise use `kurse_manuell.csv` |
| p2pool "unhealthy" | node not yet in sync, or ZMQ port mismatch (18084) |
| Warning about two Compose files | keep only `compose.yaml` |
