# Computer setup (macOS)

🌐 [Deutsch](../de/setup-mac.md) · **English** · [Français](../fr/setup-mac.md) · [Español](../es/setup-mac.md)

Written for macOS on Apple Silicon; on Linux the steps are analogous (XMRig from your package manager or
xmrig.com, power measurement e.g. with a metering plug).

## 1. Install XMRig

```bash
# Homebrew, if `brew` is missing
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

brew install xmrig          # Homebrew build: DONATE 0 %
```

## 2. Pool address and API token

```bash
ipconfig getifaddr en0                      # this computer's IP – reserve it in your router
mkdir -p ~/.config/moneta
echo '<NAS-IP>:3333' > ~/.config/moneta/pool
openssl rand -hex 16 > ~/.config/moneta/xmrig-token
chmod 600 ~/.config/moneta/xmrig-token
cat ~/.config/moneta/xmrig-token            # goes into the ledger's config.toml as token
```

## 3. Measure hashrate and extra power draw

Tab 1 – generate load (without a pool), using the thread count you intend to run later:

```bash
xmrig --bench=10M          # all cores
xmrig --bench=10M -t 3     # e.g. 3 threads
```

Tab 2 – measure after ~1 minute, then stop XMRig and measure again at idle:

```bash
deploy/mac/strom-messen.sh
```

Extra power = load − idle, **+10 %** for power-supply losses, rounded up slightly for RAM (which `powermetrics`
does not measure). Enter the result as `watts`, and the date and method as `note`, in `config.toml`.
Measure again if you change the thread count (takes effect from then on).

### Reference values (11/2026, XMRig 6.26.0, macOS, no huge pages)

| Device | Threads | Hashrate | Extra power (powermetrics) | Remarks |
|---|---|---|---|---|
| MacBook Pro M3 Pro (11 cores) | 11 | ≈ 3,700–3,800 H/s | ≈ 10 W (+10 % → 12 W used) | no throttling, ≈ 367 H/W |
| MacBook Pro M3 Pro | 6 | ≈ 2,780 H/s | ≈ 9.7 W | less efficient |
| MacBook Air M1 (fanless) | 4 | ≈ 1,730 → 1,400 H/s | ≈ 9 W (→ 11 W used) | throttles after ~5 min |

Got numbers for another device? Please share them via an issue ("Device measurement") – see
[CONTRIBUTING](../../CONTRIBUTING.md).

## 4. Mine

Only once the node is in sync and P2Pool reports "healthy":

```bash
deploy/mac/xmrig-start.sh        # all cores
deploy/mac/xmrig-start.sh 3      # 3 threads
```

On first start, macOS asks whether to allow incoming connections for `xmrig` → **Allow** (XMRig API for the
ledger). Test from the NAS:

```bash
curl -s -H "Authorization: Bearer <token>" http://<COMPUTER-IP>:18000/2/summary | head -c 200
```

Notes:
- Only on mains power (`--pause-on-battery`); for laptops set a charge limit of ~80 % (e.g. AlDente) and use a
  hard surface.
- `MEMORY 98 %` in XMRig's output is the macOS cache; what matters is memory pressure in Activity Monitor.
- "huge pages unavailable" is normal on macOS.
- Windows: Smart App Control blocks XMRig with no way to add an exception; consider WSL2.

## 5. Mining wallet

```bash
brew install monero
mkdir -p ~/Monero/wallet
monero-wallet-cli --offline --generate-new-wallet ~/Monero/wallet/mining
```

- Write the seed words on paper (English seed language for best compatibility); never store them digitally.
- `set setup-background-mining 0` – otherwise the wallet would have the node solo-mine.
- `address` shows the primary address (`4…`) for `.env`; `viewkey` shows the (secret) view key for the ledger.

Balance and transfers against your own node:

```bash
monero-wallet-cli --wallet-file ~/Monero/wallet/mining --daemon-address <NAS-IP>:18089 --trusted-daemon
```

Useful commands: `refresh`, `balance`, `show_transfers`, `transfer <address> <amount>`, `sweep_all <address>`,
`export_transfers in output=<file.csv>`. Mined XMR is locked for ~2 hours (60 blocks).
Record every transfer afterwards in the ledger under **Abgänge** (outflows).
