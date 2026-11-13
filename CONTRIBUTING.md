# Contributing to Moneta

🌐 **English** · [Deutsch](CONTRIBUTING.de.md) · [Français](CONTRIBUTING.fr.md) · [Español](CONTRIBUTING.es.md)

Thank you for wanting to help! Moneta is a small hobby project, and every contribution counts – a measurement
from your device, a translation, a bug report or a pull request. You can write issues and pull requests in
**English, German, French or Spanish**.

By participating you agree to our [code of conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

| You have … | You could … |
|---|---|
| 10 minutes | Share hashrate and power numbers for your device ("Device measurement" issue form) |
| an hour | Fix a typo, improve a guide, update an outdated translation |
| an evening | Write a guide (Linux, Windows/WSL2, QNAP, Unraid, TrueNAS …), pick a [good first issue](https://github.com/nexovaanalytics-oss/Moneta/labels/good%20first%20issue) |
| more time | Translate the dashboard and report, add a tax profile for your country, build the arm64 image – see the [roadmap](ROADMAP.md) |

Ideas and questions are welcome too – open an issue or start a discussion.

## Before you start

- Check the [issues](https://github.com/nexovaanalytics-oss/Moneta/issues) and the [roadmap](ROADMAP.md) –
  maybe someone is already working on it.
- For larger changes, please open an issue first and describe your plan. That saves everyone time.
- Read [architecture](docs/en/architecture.md) and [design decisions](docs/en/design-decisions.md) to
  understand why things are built the way they are.

## Development setup

```bash
git clone https://github.com/<your-account>/Moneta.git
cd Moneta
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r ledger/requirements.txt pytest
python -m pytest -q ledger/tests              # runs without internet (fake wallet, fake XMRig, fake prices)
docker build -f ledger/Dockerfile .           # build context is the repository root
```

You do not need a Monero node or a miner to work on the ledger – the tests simulate both.

## Ground rules

**Privacy first – this is a public repository.**
- Never commit secrets: seed, passwords, view key, tokens, `config.toml`, `.env`, databases, wallet files.
- No personal environment data: real IP addresses, user names, mining addresses, host names, your own servers or
  hosting providers. Use placeholders such as `<NAS-IP>`, `<NAS-USER>`, `4...`.
- Check `git status` and `git diff --cached` before every commit.

**Code (`ledger/`)**
- Python 3.12, standard library + `openpyxl` (+ `tzdata`) only. New dependencies need a good reason and an entry in
  [`THIRD_PARTY.md`](THIRD_PARTY.md).
- New source files start with `# SPDX-License-Identifier: EUPL-1.2`.
- **Tax-relevant data is immutable:** stored prices, watts, tariffs and costs are never recalculated afterwards.
  Configuration changes only apply going forward.
- **Database migrations are additive only:** append new entries to `db.MIGRATIONS`, never change existing ones.
- Amounts in piconero (`int`), money as `Decimal`; round EUR per inflow to the cent, then sum.
- External requests must not allow conclusions about the timing of individual payouts.
- POST endpoints only with a same-origin check; the dashboard is meant for the LAN only.
- `python -m pytest -q ledger/tests` must pass; new features come with tests (fake services, no internet).
- Comments in English or German. The UI is currently German – UI strings will move to translation files (see
  roadmap), so please keep new UI text short and easy to extract.

## Documentation and translations

- Docs live in `docs/<de|en|fr|es>/` with **identical file names**; each page starts with a language switcher.
- German is the reference version. If you change a page, update the other languages if you can – if not, say so
  in the pull request and we will sync them (or open a "Translation" issue).
- Tax pages describe German law. Keep legal references (§ 22 no. 3 EStG, § 23 EStG, BMF circular of 6 March
  2025) exact; describe what the tool calculates, do not give tax advice.
- Current figures (prices, hashrate, difficulty, electricity prices) always with a date and source.
- A new language is very welcome: create `docs/<code>/` with the same file names and add it to
  [`docs/README.md`](docs/README.md) and the language switchers.

## Pull requests

1. Fork the repository and create a branch (`fix/…`, `feat/…`, `docs/…`).
2. Keep pull requests small and focused; describe *what* and *why*.
3. Add an entry under "Unreleased" in [`CHANGELOG.md`](CHANGELOG.md) for user-facing changes.
4. Make sure the tests pass and the checklist in the pull request template is complete.

Maintainers review in their spare time – please allow a few days. Releases are cut by the maintainers
(tag `ledger-vX.Y.Z`, see [operations](docs/en/operations.md)).

## AI-assisted contributions

Contributions made with the help of AI tools are welcome. The repository contains a [`CLAUDE.md`](CLAUDE.md) with
the project rules for coding assistants. You remain responsible for your contribution: review it, test it, and
make sure it contains no secrets or personal data.

## Security

Please do **not** report vulnerabilities in public issues – see [SECURITY.md](SECURITY.md).

## License

Moneta is licensed under the [EUPL-1.2](LICENSE). By submitting a contribution, you agree that it is licensed
under the EUPL-1.2 as well.
