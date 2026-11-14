# Exploitation

🌐 [Deutsch](../de/operations.md) · [English](../en/operations.md) · **Français** · [Español](../es/operations.md)

Exécutez toutes les commandes NAS via SSH dans le dossier du projet (exemple : `/volume1/docker/monero`), toujours
avec le même nom de projet (`-p monero-pool` – à adapter au nom utilisé dans Container Manager si besoin).

## Aide-mémoire

```bash
sudo docker ps --format "table {{.Names}}\t{{.Status}}"   # vue d'ensemble
sudo docker logs --tail 5 monerod                          # progression de la synchronisation
sudo docker exec monerod monerod status                    # hauteur, pairs, hashrate
sudo docker attach p2pool                                  # puis "status" ; détacher avec Ctrl+P, Ctrl+Q (pas Ctrl+C !)
sudo docker logs --tail 30 xmr-ledger                      # ledger
sudo docker logs --tail 30 wallet-rpc                      # portefeuille en lecture seule
sudo docker restart xmr-ledger                             # après modification de config.toml
```

## Publier une version du ledger

Sur votre ordinateur, dans le dépôt :

```bash
python -m pytest -q ledger/tests                 # doit passer
# compléter CHANGELOG.md, commit, push → image :edge
git tag ledger-v1.2.0 && git push origin ledger-v1.2.0   # → image :1.2.0
```

Ou dans le navigateur : GitHub → dépôt → **Releases → Draft a new release** → créer le nouveau tag
`ledger-v1.2.0` (cible : `main`) → titre p. ex. « Ledger 1.2.0 », texte tiré de `CHANGELOG.md` →
**Publish release**.

Attendre ensuite GitHub → Actions → workflow « ledger » (tests + image).

## Accès à l'image

L'image `ghcr.io/nexovaanalytics-oss/xmr-ledger` est publique ; aucun `docker login` n'est nécessaire.
Pour l'image d'un fork privé : `sudo docker login ghcr.io -u <utilisateur-github>` avec un jeton (classic)
disposant de `read:packages`.

## Déployer une nouvelle version du ledger sur le NAS

**Avec le script de mise à jour** (recommandé) : il demande à GitHub la dernière version `ledger-vX.Y.Z`,
affiche le changement et demande confirmation. Il télécharge ensuite l'image (rien n'est modifié avant), sauvegarde
la base de données dans le conteneur en cours d'exécution (`ledger/data/ledger-vor-X.Y.Z-<heure>.sqlite`, sauvegarde
SQLite WAL compris), règle `LEDGER_VERSION` dans `.env`, redémarre `wallet-rpc` et `ledger`, puis affiche le journal
et la marche à suivre pour revenir en arrière. La version reste figée – le script ne s'exécute que si vous le lancez.
À télécharger une fois (lisez-le d'abord) :

```bash
cd /volume1/docker/monero
sudo curl -fsSLo update-ledger.sh https://raw.githubusercontent.com/nexovaanalytics-oss/Moneta/main/deploy/nas/update-ledger.sh
cat update-ledger.sh
```

Ensuite, à chaque mise à jour :

```bash
cd /volume1/docker/monero
sudo bash update-ledger.sh --check     # afficher seulement : version figée vs. dernière version
sudo bash update-ledger.sh             # dernière version, avec confirmation
sudo bash update-ledger.sh 1.2.0       # une version précise
```

La seule requête externe va à `api.github.com` (liste des releases) – au moment que vous choisissez, sans lien avec
les paiements.

**À la main :**

```bash
cd /volume1/docker/monero
sudo sed -i 's/^LEDGER_VERSION=.*/LEDGER_VERSION=1.2.0/' .env
sudo docker compose -p monero-pool pull wallet-rpc ledger
sudo docker compose -p monero-pool up -d wallet-rpc ledger
sudo docker logs --tail 10 xmr-ledger            # la ligne de démarrage indique la version et le schéma de BD
```

Revenir en arrière : remettre `LEDGER_VERSION`, relancer `up -d`. Attention : les migrations de la base de
données ne vont que vers l'avant – sauvegardez `ledger/data/` avant les mises à jour importantes.

## Mises à jour de Monero et P2Pool

- **monerod/p2pool :** `sudo docker compose -p monero-pool pull monerod p2pool && sudo docker compose -p monero-pool up -d`.
  Obligatoire avant les hard forks (annonces sur getmonero.org et dans le dépôt P2Pool).
- **wallet-rpc dans l'image du ledger :** augmenter `ARG MONERO_VERSION` dans `ledger/Dockerfile`, publier une
  nouvelle version du ledger. Le build échoue si la version ne figure pas dans getmonero.org/downloads/hashes.txt.

## Sauvegarde

- Inclure `ledger/data/` (base de données, `config.toml`, `kurse_manuell.csv`) et `.env` dans la sauvegarde
  (p. ex. Hyper Backup).
- `ledger/wallets/` n'a pas besoin d'être sauvegardé (recréable depuis la clé de visualisation).
- Ne pas sauvegarder le volume de la blockchain (resynchronisable).
- Mots de la phrase de récupération du portefeuille de minage : sur papier uniquement.

## Dépannage

| Symptôme | Cause / solution |
|---|---|
| Ledger : « Wallet-Sync fehlgeschlagen: … refused » | wallet-rpc démarre encore ; revérifier après 2 min |
| Ledger : erreurs de synchronisation du portefeuille jusqu'à la synchro du nœud | normal tant que monerod se synchronise |
| Appareil « nicht erreichbar » (injoignable) | XMRig ne tourne pas avec `--http-host 0.0.0.0`, ordinateur en veille, pare-feu macOS, mauvaise IP |
| Journal : « XMRig-API lehnt das Token ab » (jeton refusé) | jeton dans `config.toml` ≠ fichier jeton sur l'ordinateur |
| Appareil « pausiert » (en pause) | XMRig joignable mais sans hashrate (pool injoignable, sur batterie, en pause) – ne coûte rien |
| Entrée « Kurs fehlt » (cours manquant) | rattrapé lors de la prochaine récupération des cours ; sinon `kurse_manuell.csv` |
| p2pool « unhealthy » | nœud pas encore synchronisé, ou port ZMQ incorrect (18084) |
| Avertissement « deux fichiers Compose » | ne garder que `compose.yaml` |
