# Contribuer à Moneta

🌐 [English](CONTRIBUTING.md) · [Deutsch](CONTRIBUTING.de.md) · **Français** · [Español](CONTRIBUTING.es.md)

Merci de vouloir aider ! Moneta est un petit projet de loisir, et chaque contribution compte – une mesure de votre
appareil, une traduction, un rapport de bug ou une pull request. Vous pouvez rédiger issues et pull requests en
**français, anglais, allemand ou espagnol**.

En participant, vous acceptez notre [code de conduite](CODE_OF_CONDUCT.fr.md).

## Comment contribuer

| Vous avez … | Vous pourriez … |
|---|---|
| 10 minutes | Partager le hashrate et la consommation de votre appareil (formulaire d'issue « Device measurement ») |
| une heure | Corriger une coquille, améliorer un guide, mettre à jour une traduction |
| une soirée | Écrire un guide (Linux, Windows/WSL2, QNAP, Unraid, TrueNAS …), prendre une [good first issue](https://github.com/nexovaanalytics-oss/Moneta/labels/good%20first%20issue) |
| plus de temps | Traduire le tableau de bord et le rapport, ajouter un profil fiscal pour votre pays, construire l'image arm64 – voir la [feuille de route](ROADMAP.md) |

Les idées et les questions sont aussi les bienvenues – via une issue ou dans les Discussions.

## Avant de commencer

- Consultez les [issues](https://github.com/nexovaanalytics-oss/Moneta/issues) et la
  [feuille de route](ROADMAP.md) – quelqu'un y travaille peut-être déjà.
- Pour des changements importants, ouvrez d'abord une issue décrivant votre projet. Tout le monde y gagne du
  temps.
- Lisez [l'architecture](docs/fr/architecture.md) et les [décisions de conception](docs/fr/design-decisions.md)
  pour comprendre pourquoi les choses sont construites ainsi.

## Environnement de développement

```bash
git clone https://github.com/<votre-compte>/Moneta.git
cd Moneta
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r ledger/requirements.txt pytest
python -m pytest -q ledger/tests              # fonctionne sans Internet (faux portefeuille, faux XMRig, faux cours)
docker build -f ledger/Dockerfile .           # le contexte de build est la racine du dépôt
```

Pour travailler sur le ledger, vous n'avez besoin ni d'un nœud Monero ni d'un mineur – les tests simulent les deux.

## Règles de base

**La confidentialité d'abord – c'est un dépôt public.**
- Ne jamais committer de secrets : phrase de récupération, mots de passe, clé de visualisation, jetons,
  `config.toml`, `.env`, bases de données, fichiers de portefeuille.
- Aucune donnée personnelle d'environnement : vraies adresses IP, noms d'utilisateur, adresses de minage, noms
  d'hôtes, vos propres serveurs ou hébergeurs. Utilisez des paramètres fictifs comme `<IP-NAS>`,
  `<UTILISATEUR-NAS>`, `4...`.
- Vérifiez `git status` et `git diff --cached` avant chaque commit.

**Code (`ledger/`)**
- Python 3.12, bibliothèque standard + `openpyxl` (+ `tzdata`) uniquement. Toute nouvelle dépendance doit être
  justifiée et ajoutée à [`THIRD_PARTY.md`](THIRD_PARTY.md).
- Les nouveaux fichiers source commencent par `# SPDX-License-Identifier: EUPL-1.2`.
- **Les données fiscales sont immuables :** les cours, watts, tarifs et coûts enregistrés ne sont jamais
  recalculés après coup. Les changements de configuration ne valent que pour l'avenir.
- **Migrations de base de données uniquement additives :** ajouter les nouvelles entrées à la fin de
  `db.MIGRATIONS`, ne jamais modifier les existantes.
- Montants en piconero (`int`), argent en `Decimal` ; arrondir l'EUR au centime par entrée, puis additionner.
- Les requêtes externes ne doivent pas permettre de déduire l'heure des paiements individuels.
- Points de terminaison POST uniquement avec contrôle same-origin ; le tableau de bord est destiné au LAN.
- `python -m pytest -q ledger/tests` doit passer ; les nouvelles fonctionnalités sont accompagnées de tests
  (services simulés, sans Internet).
- Commentaires en anglais ou en allemand. L'interface est pour l'instant en allemand – ses textes seront déplacés
  dans des fichiers de traduction (voir la feuille de route) ; gardez donc les nouveaux textes courts et faciles à
  extraire.

## Documentation et traductions

- La documentation se trouve dans `docs/<de|en|fr|es>/` avec des **noms de fichiers identiques** ; chaque page
  commence par un sélecteur de langue.
- L'allemand est la version de référence. Si vous modifiez une page, mettez à jour les autres langues si vous le
  pouvez – sinon, signalez-le dans la pull request et nous les synchroniserons (ou ouvrez une issue
  « Translation »).
- Les pages fiscales décrivent le droit allemand. Citez les normes exactement (§ 22 n° 3 EStG, § 23 EStG,
  circulaire du BMF du 6 mars 2025) ; décrivez ce que calcule l'outil, sans donner de conseil fiscal.
- Chiffres actuels (cours, hashrate, difficulté, prix de l'électricité) toujours avec date et source.
- Une nouvelle langue est la bienvenue : créez `docs/<code>/` avec les mêmes noms de fichiers et ajoutez-la à
  [`docs/README.md`](docs/README.md) et aux sélecteurs de langue.

## Pull requests

1. Forkez le dépôt et créez une branche (`fix/…`, `feat/…`, `docs/…`).
2. Gardez les pull requests petites et ciblées ; décrivez *quoi* et *pourquoi*.
3. Pour les changements visibles, ajoutez une entrée sous « Unreleased » dans [`CHANGELOG.md`](CHANGELOG.md).
4. Les tests doivent passer et la liste de contrôle du modèle de pull request doit être complète.

Les relectures se font sur du temps libre – merci de prévoir quelques jours. Les versions sont publiées par les
mainteneurs (tag `ledger-vX.Y.Z`, voir [exploitation](docs/fr/operations.md)).

## Contributions assistées par IA

Les contributions réalisées avec l'aide d'outils d'IA sont les bienvenues. Le dépôt contient un
[`CLAUDE.md`](CLAUDE.md) avec les règles du projet pour les assistants de code. Vous restez responsable de votre
contribution : relisez-la, testez-la et assurez-vous qu'elle ne contient ni secrets ni données personnelles.

## Sécurité

Merci de ne **pas** signaler de vulnérabilités dans des issues publiques – voir [SECURITY.md](SECURITY.md).

## Licence

Moneta est sous licence [EUPL-1.2](LICENSE). En soumettant une contribution, vous acceptez qu'elle soit également
placée sous EUPL-1.2.
