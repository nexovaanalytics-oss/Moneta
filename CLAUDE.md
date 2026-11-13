# CLAUDE.md – working rules for this repository

**Moneta** is a public project (EUPL-1.2): a NAS stack for Monero mining with your own node and P2Pool, plus the
**XMR-Ledger** (`ledger/`) for tax documentation. Before making changes, read `docs/de/architecture.md` (or
`docs/en/…`) and `docs/de/design-decisions.md`. Human contributors follow the same rules in `CONTRIBUTING.md`.

## Languages

- Project language for community files (README, CONTRIBUTING, CHANGELOG, SECURITY, ROADMAP, issue/PR templates):
  **English**. README, CONTRIBUTING and CODE_OF_CONDUCT also exist as `*.de.md`, `*.fr.md`, `*.es.md` – keep them
  in sync when the English version changes.
- Docs live in `docs/<de|en|fr|es>/` with identical file names and a language switcher at the top of each page.
  **German is the reference.** When changing a page, update all four languages; if that is not possible, say so
  in the PR description.
- Dashboard, Excel report, config comments and script messages are currently German (UI translation is on the
  roadmap). Code comments in English or German.
- Tax terms precise (§ 22 no. 3, § 23 EStG, BMF circular of 6 March 2025); never phrase tax advice – describe
  how the tool calculates.
- Current figures (prices, hashrate, difficulty, electricity prices) never from memory – look them up, with date.

## Public repository – what must not go in

- No secrets: seed, passwords, view key, tokens, `config.toml`, `.env`, databases, wallet files.
- No personal environment data: real IP addresses, user names, mining addresses, host names, own servers or
  hosting providers. Use placeholders in docs and examples (`<NAS-IP>`, `<NAS-USER>`, `4...`).
- Check `git status` and `git diff --cached` before every commit.

## Code rules (ledger/)

- Python 3.12, standard library + `openpyxl` (+ `tzdata`) only. New dependencies only with justification and an
  entry in `THIRD_PARTY.md`.
- New source files start with `# SPDX-License-Identifier: EUPL-1.2`.
- **Tax-relevant data is immutable:** stored prices, watts, tariffs and costs are never recalculated afterwards.
  Configuration changes only apply going forward.
- **DB migrations are additive only:** append new entries to `db.MIGRATIONS`, never change existing ones.
- Amounts in piconero (int), money as `Decimal`; round EUR per inflow to the cent, then sum.
- External requests must not allow conclusions about the timing of individual payouts.
- POST endpoints only with a same-origin check; dashboard for the LAN only.
- `python -m pytest -q ledger/tests` must pass; new features get tests (fake services, no internet).
- Docker build context is the repository root: `docker build -f ledger/Dockerfile .`

## Releases

- SemVer per component, Git tag `ledger-vX.Y.Z` (e.g. via GitHub → Releases); maintain `CHANGELOG.md`.
- GitHub Actions builds `ghcr.io/nexovaanalytics-oss/xmr-ledger:X.Y.Z` (or `:edge` from `main`).
- On the server the version is pinned deliberately in `.env` (`LEDGER_VERSION`) – no auto-update.
- Fundamental decisions go into a new entry in `docs/<lang>/design-decisions.md` (all four languages).
