# Security

🌐 Reports are welcome in English, Deutsch, Français or Español.

## Reporting a vulnerability

Please **do not open a public issue**. Report security problems privately via
**GitHub → Security → [Report a vulnerability](https://github.com/nexovaanalytics-oss/Moneta/security/advisories/new)**
in this repository. You will usually get a response within a week.

## Supported versions

Security fixes are provided for the latest `ledger` release.

## Security model (short)

- The ledger only works with **address + view key**; the spend key never belongs on the server.
- Dashboard (Basic Auth, same-origin check for forms), Stratum and RPC are meant **for the LAN only** – no port
  forwarding to the internet. Use a VPN for remote access.
- `config.toml` and `.env` contain secrets (view key, passwords, tokens) and must never be committed.
- External price requests do not contain payout times.
