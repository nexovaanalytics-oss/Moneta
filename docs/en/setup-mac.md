# Computer setup (macOS)

🌐 [Deutsch](../de/setup-mac.md) · **English** · [Français](../fr/setup-mac.md) · [Español](../es/setup-mac.md)

Written for macOS on Apple Silicon; on Linux the steps are analogous (XMRig from your package manager or
xmrig.com, power measurement e.g. with a metering plug).

## Quick setup: installer and menu bar app

The installer covers steps 1, 2 and 4 and sets up XMRig as a launchd agent with the menu bar app
**Moneta Miner** (macOS 13 or later). It is safe to run again (e.g. after `git pull`); existing settings are
kept.

```bash
git clone https://github.com/nexovaanalytics-oss/Moneta.git ~/Moneta
~/Moneta/deploy/mac/install.sh
```

What the installer does:
- installs Homebrew and XMRig if needed (Homebrew build, DONATE 0 %);
- asks for the pool address and the number of threads and creates the API token – or takes a token that is
  already in `config.toml` for this computer;
- copies the scripts to `~/Library/Application Support/Moneta/` and creates the launchd agent `moneta.xmrig`
  (log `~/Library/Logs/Moneta/xmrig.log`, restart after a crash, optional autostart at login);
- builds the menu bar app with `swiftc` from the Command Line Tools into `~/Applications/Moneta Miner.app` and
  starts it at login. Because it is built on the computer itself, it needs neither an Apple developer account
  nor a Gatekeeper exception;
- if the macOS firewall is on, allows incoming connections for `xmrig` (two `sudo` commands, after asking).
  Run the installer again after `brew upgrade xmrig` – the rule is tied to the program path;
- prints a ready-made `[[miner]]` block for the ledger's `config.toml` (also saved to
  `~/.config/moneta/ledger-miner.toml`).

Then, in this order: reserve the computer's IP in the router → measure the extra power draw (section 3) → add the
block with the measured `watts` to `config.toml` → `sudo docker restart xmr-ledger` on the NAS → **Miner
starten** in the menu bar. Watts are frozen with every sample; a placeholder value cannot be corrected later.

Without prompts (e.g. for several computers): `POOL=<NAS-IP>:3333 THREADS=3 AUTOSTART=n FIREWALL=j START=n
~/Moneta/deploy/mac/install.sh`. Remove: `~/Moneta/deploy/mac/install.sh --uninstall` (settings, log and XMRig
are kept).

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

Set up with the installer: menu bar → **Moneta Miner** → *Miner starten* / *Miner stoppen* (start/stop); it
also offers threads, autostart at login, hashrate, pool connection and the log. The same in the terminal:

```bash
MM="$HOME/Library/Application Support/Moneta/moneta-miner.sh"
"$MM" start                  # or stop, restart
"$MM" status
"$MM" threads 3              # or: all – restarts XMRig if it is running
"$MM" autostart on           # or: off
"$MM" log -f
```

Without the installer, by hand in the foreground:

```bash
deploy/mac/xmrig-start.sh        # threads from ~/.config/moneta/threads, otherwise all cores
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
