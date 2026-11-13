# Third-party software and data sources

Moneta itself is licensed under the [EUPL-1.2](LICENSE). The `xmr-ledger` container image additionally contains
or uses the following software and services, each with its own license and terms.

## Included in the image

| Component | License | Notes |
|---|---|---|
| Monero – `monero-wallet-rpc` | BSD-3-Clause, © The Monero Project | Official Linux binary, checksum verified against getmonero.org/downloads/hashes.txt. License text in the image: `/usr/share/doc/monero/LICENSE`. Source: https://github.com/monero-project/monero |
| openpyxl | MIT | Excel export. https://foss.heptapod.net/openpyxl/openpyxl |
| tzdata (Python package) | Apache-2.0 | Time zone data |
| Python 3.12 (base image `python:3.12-slim`) | PSF License | https://hub.docker.com/_/python |
| Debian packages in the base image (incl. curl, bzip2, ca-certificates, tzdata) | their respective licenses | License texts in the image under `/usr/share/doc/<package>/copyright` |

## Referenced only, not distributed

| Component | License | Use |
|---|---|---|
| XMRig | GPL-3.0 | Miner on the computers, installed separately |
| P2Pool | GPL-3.0 | Decentralized pool, image `ghcr.io/sethforprivacy/p2pool` |
| Monero node (`monerod`) | BSD-3-Clause | Image `ghcr.io/sethforprivacy/simple-monerod` |

## Data source

**CoinGecko API** – price data. The dashboard names the source ("Kursdaten: CoinGecko"). Use is subject to
CoinGecko's API terms (including attribution and the rate limits of the free tier); every operator is responsible
for complying with them.

## Documents

| File | Source | License |
|---|---|---|
| `CODE_OF_CONDUCT*.md` | Contributor Covenant 3.0 and its official translations, https://www.contributor-covenant.org | CC BY-SA 4.0 |
