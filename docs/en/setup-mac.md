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
- installs Homebrew and XMRig if needed (Homebrew build; like all official builds it donates at least 1 % to the
  XMRig developers, `--donate-level 0` is ignored);
- **looks for the XMR ledger in the home network** (every address of your /24 network on port 8090,
  `GET /api/moneta`) and takes the pool address from it. If none is found, it asks for the pool address as before
  (or set `LEDGER=http://<NAS-IP>:8090`);
- creates the API token – or takes a token that is already in `config.toml` for this computer;
- **suggests the number of threads**: from the profile table [`deploy/mac/profile.tsv`](../../deploy/mac/profile.tsv)
  (measured devices) or by rule of thumb – fanless (MacBook Air): performance cores − 1, with a fan: all cores.
  On request it measures right away (see section 3);
- copies the scripts to `~/Library/Application Support/Moneta/` and creates the launchd agent `moneta.xmrig`
  (log `~/Library/Logs/Moneta/xmrig.log`, restart after a crash, optional autostart at login);
- builds the menu bar app with `swiftc` from the Command Line Tools into `~/Applications/Moneta Miner.app` and
  starts it at login. Because it is built on the computer itself, it needs neither an Apple developer account
  nor a Gatekeeper exception;
- if the macOS firewall is on, allows incoming connections for `xmrig` (two `sudo` commands, after asking).
  Run the installer again after `brew upgrade xmrig` – the rule is tied to the program path;
- **pairs the computer with the ledger**: create a pairing code in the dashboard under **Geräte** and enter it
  in the installer. The computer reports its name, address, token, device profile and – if measured – threads
  and extra power draw. Without a ledger or code it prints a `[[miner]]` block as before
  (`~/.config/moneta/ledger-miner.toml`).

Then: in the dashboard under **Geräte**, **approve** the computer with its measured extra power draw (pre-filled
from the measurement) and click **Miner starten** in the menu bar. The ledger only records the computer from
approval onwards; watts are frozen with every sample. A fixed IP in the router is still recommended but no longer
required: on every start the computer reports to the ledger (`moneta-miner.sh heartbeat`), and a changed IP is
taken over.

XMRig logs in to P2Pool with the device name (`~/.config/moneta/name`, taken from the ledger for paired
computers). The ledger uses it to attribute shares and payouts to the computer, even if P2Pool only sees an
internal address on the Docker network ([Payout → computer](ledger.md#payout--computer)). Computers set up
earlier: `git pull` and run `install.sh` again.

Without prompts (e.g. for several computers): `LEDGER=http://<NAS-IP>:8090 CODE=<code> THREADS=3 MEASURE=n
AUTOSTART=n FIREWALL=j START=n ~/Moneta/deploy/mac/install.sh`. Remove: `~/Moneta/deploy/mac/install.sh
--uninstall` (settings, log and XMRig are kept).

## 1. Install XMRig

```bash
# Homebrew, if `brew` is missing
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

brew install xmrig          # Homebrew build; DONATE 1 % (upstream minimum)
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

**Automatically:** `deploy/mac/einmessen.sh` (offered by the installer, afterwards also at
`~/Library/Application Support/Moneta/einmessen.sh`) measures idle power and then hashrate and power in steps up
to all cores – fanless: performance cores − 1, all performance cores, plus half of the efficiency cores and all
cores (M4 with 4 + 6 cores: 3, 4, 7, 10); with a fan: performance cores, half of the efficiency cores and all.
Steps run in ascending order after a warm-up (fanless 5 min so that throttling is captured). Extra power draw =
(load − idle) × 1.1, rounded up, with a ready-made note.

The suggestion is the step with the highest balance of calculated revenue and electricity cost per day: revenue =
hashrate × 86,400 ÷ difficulty × block reward × price, electricity = extra power × 24 h × tariff. The figures
come from your own ledger (difficulty from the node, local price, tariff from `config.toml`); a further step only
pays if its extra revenue exceeds its extra electricity. Without figures from the ledger, the best hashrate per
watt is used. The table shows every step and the installer lets you pick any of them. The calculation guides the
thread choice; it is not a tax figure.

Takes ≈ 10 min with a fan, ≈ 30 min fanless; connect the power adapter, do not use the Mac meanwhile, `sudo` for
`powermetrics`. Your own steps: `einmessen.sh 3 4 6`. The measurement already mines via P2Pool. Pairing sends the
result (`~/.config/moneta/einmessung.json`) along as a suggestion.

**By hand:**

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

### Rules of thumb

Hashrate and extra power draw depend on chip, cooling and thread count. Rules of thumb: Macs with a fan run on
all cores without noticeable throttling. Fanless Macs (MacBook Air) throttle under sustained load after a few
minutes; there, performance cores − 1 usually gives the better hashrate per watt. `einmessen.sh` measures the
values for your own device; thread recommendations per chip are in
[`deploy/mac/profile.tsv`](../../deploy/mac/profile.tsv).

Got numbers for another device? Please share them via an issue ("Device measurement") – see
[CONTRIBUTING](../../CONTRIBUTING.md).

## 4. Mine

Only once the node is in sync and P2Pool reports "healthy":

Set up with the installer: menu bar → **Moneta Miner** → *Miner starten* / *Miner stoppen* (start/stop); it
also offers threads, autostart at login, the log and a jump to the dashboard. The app window shows how this Mac
is doing:

- the current hashrate next to the menu bar icon (can be switched off),
- the history of the last 15 min / 1 h / 6 h with a *mining / paused / stopped* timeline, average hashrate and
  paused time (kept in the app's memory only; the dashboard shows the history over days),
- the hashrate per thread (e.g. to spot slower efficiency cores), pool ping and accepted/rejected stratum shares
  (not P2Pool's sidechain shares),
- power source, battery level and thermal state – and, when mining pauses, the **reason**: XMRig runs with
  `--pause-on-battery` and pauses as soon as macOS runs on battery. This also happens with the power adapter
  plugged in when a charge limiter such as AlDente lets the battery discharge to its lower limit; the app
  detects running charge-limiter apps and a connected adapter and says so. It also warns about Low Power Mode
  and thermal throttling.

The *Dashboard* button opens `http://<pool-host>:8090`; put a different address into `~/.config/moneta/dashboard`.
To update: `git pull`, then run `deploy/mac/install.sh` again (settings are kept).

The same in the terminal:

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
