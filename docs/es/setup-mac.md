# Instalación en el equipo (macOS)

🌐 [Deutsch](../de/setup-mac.md) · [English](../en/setup-mac.md) · [Français](../fr/setup-mac.md) · **Español**

Escrito para macOS con Apple Silicon; en Linux los pasos son análogos (XMRig desde el gestor de paquetes o
xmrig.com, medición del consumo p. ej. con un enchufe medidor).

## Instalación rápida: instalador y app de la barra de menús

El instalador cubre los pasos 1, 2 y 4 y configura XMRig como agente de launchd con la app de la barra de menús
**Moneta Miner** (macOS 13 o posterior). Puede ejecutarse de nuevo sin riesgo (p. ej. tras `git pull`); los
ajustes existentes se conservan.

```bash
git clone https://github.com/nexovaanalytics-oss/Moneta.git ~/Moneta
~/Moneta/deploy/mac/install.sh
```

Qué hace el instalador:
- instala Homebrew y XMRig si hace falta (build de Homebrew; como todos los builds oficiales, dona al menos un 1 %
  a los desarrolladores de XMRig, `--donate-level 0` se ignora);
- **busca el XMR-Ledger en la red doméstica** (todas las direcciones de tu red /24 en el puerto 8090,
  `GET /api/moneta`) y toma de él la dirección del pool. Si no encuentra ninguno, pide la dirección del pool como
  antes (o indica `LEDGER=http://<IP-NAS>:8090`);
- crea el token de la API – o usa un token que ya figure en `config.toml` para este equipo;
- **propone el número de hilos**: según la tabla de perfiles [`deploy/mac/profile.tsv`](../../deploy/mac/profile.tsv)
  (equipos medidos) o por regla general – sin ventilador (MacBook Air): núcleos de rendimiento − 1; con
  ventilador: todos los núcleos. Si lo deseas, mide en el momento (ver sección 3);
- copia los scripts a `~/Library/Application Support/Moneta/` y crea el agente de launchd `moneta.xmrig`
  (registro `~/Library/Logs/Moneta/xmrig.log`, reinicio tras un fallo, inicio al iniciar sesión opcional);
- compila la app de la barra de menús con `swiftc` de las Command Line Tools en `~/Applications/Moneta Miner.app`
  y la abre al iniciar sesión. Como se compila en el propio equipo, no necesita cuenta de desarrollador de Apple
  ni una excepción de Gatekeeper;
- si el firewall de macOS está activado, permite conexiones entrantes para `xmrig` (dos comandos `sudo`, tras
  preguntar). Tras `brew upgrade xmrig`, vuelve a ejecutar el instalador: la regla depende de la ruta del
  programa;
- **empareja el equipo con el ledger**: crea un código de emparejamiento en el panel en **Geräte** e introdúcelo
  en el instalador. El equipo envía su nombre, dirección, token, perfil y, si se ha medido, los hilos y el
  consumo adicional. Sin ledger o sin código, muestra como antes un bloque `[[miner]]`
  (`~/.config/moneta/ledger-miner.toml`).

Después: en el panel, en **Geräte**, **aprueba** el equipo con el consumo adicional medido (rellenado a partir de
la medición) y pulsa **Miner starten** en la barra de menús. El ledger registra el equipo solo a partir de la
aprobación; los vatios se fijan en cada registro. Una IP fija en el router sigue siendo recomendable, pero ya no
es imprescindible: en cada arranque el equipo se notifica al ledger (`moneta-miner.sh heartbeat`) y se adopta una
IP cambiada.

Sin preguntas (p. ej. para varios equipos): `LEDGER=http://<IP-NAS>:8090 CODE=<código> THREADS=3 MEASURE=n
AUTOSTART=n FIREWALL=j START=n ~/Moneta/deploy/mac/install.sh`. Desinstalar: `~/Moneta/deploy/mac/install.sh
--uninstall` (se conservan los ajustes, el registro y XMRig).

## 1. Instalar XMRig

```bash
# Homebrew, si falta `brew`
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

brew install xmrig          # build de Homebrew; DONATE 1 % (mínimo de upstream)
```

## 2. Dirección del pool y token de la API

```bash
ipconfig getifaddr en0                      # IP de este equipo – resérvala en el router
mkdir -p ~/.config/moneta
echo '<IP-NAS>:3333' > ~/.config/moneta/pool
openssl rand -hex 16 > ~/.config/moneta/xmrig-token
chmod 600 ~/.config/moneta/xmrig-token
cat ~/.config/moneta/xmrig-token            # va como token en el config.toml del ledger
```

## 3. Medir hashrate y consumo adicional

**Automáticamente:** `deploy/mac/einmessen.sh` (lo ofrece el instalador; después también en
`~/Library/Application Support/Moneta/einmessen.sh`) mide el consumo en reposo y, para dos números de hilos – sin
ventilador: núcleos de rendimiento − 1 y todos los núcleos de rendimiento; con ventilador: todos los núcleos y los
núcleos de rendimiento –, el hashrate y la potencia, siempre tras un calentamiento (5 min sin ventilador, para
captar la limitación térmica). La propuesta es el mejor hashrate por vatio; consumo adicional = (carga − reposo) ×
1,1, redondeado hacia arriba, con una nota lista. Dura ≈ 10 min con ventilador y ≈ 25 min sin él; conecta el
cargador, no uses el Mac mientras tanto, `sudo` para `powermetrics`. Candidatos propios: `einmessen.sh 3 4`. La
medición ya mina a través de P2Pool. El emparejamiento envía el resultado (`~/.config/moneta/einmessung.json`)
como propuesta.

**A mano:**

Pestaña 1 – generar carga (sin pool), con el número de hilos que usarás después:

```bash
xmrig --bench=10M          # todos los núcleos
xmrig --bench=10M -t 3     # p. ej. 3 hilos
```

Pestaña 2 – medir tras ~1 minuto, luego detener XMRig y volver a medir en reposo:

```bash
deploy/mac/strom-messen.sh
```

Consumo adicional = carga − reposo, **+10 %** por pérdidas de la fuente de alimentación, redondeado ligeramente
hacia arriba por la RAM (que `powermetrics` no mide). Anota el resultado como `watts`, y la fecha y el método
como `note`, en `config.toml`. Vuelve a medir si cambias el número de hilos (se aplica desde ese momento).

### Valores orientativos

El hashrate y el consumo adicional dependen del chip, la refrigeración y el número de hilos. Reglas generales:
los Mac con ventilador funcionan con todos los núcleos sin limitación apreciable. Los Mac sin ventilador (MacBook
Air) se limitan bajo carga continua tras unos minutos; ahí, núcleos de rendimiento − 1 suele dar el mejor
hashrate por vatio. `einmessen.sh` mide los valores de tu equipo; las recomendaciones de hilos por chip están en
[`deploy/mac/profile.tsv`](../../deploy/mac/profile.tsv).

¿Tienes mediciones de otro equipo? Compártelas mediante un issue ("Device measurement"); consulta
[CONTRIBUTING](../../CONTRIBUTING.es.md).

## 4. Minar

Solo cuando el nodo esté sincronizado y P2Pool indique "healthy":

Con el instalador: barra de menús → **Moneta Miner** → *Miner starten* / *Miner stoppen* (iniciar / detener);
ahí también están los hilos, el inicio al iniciar sesión, el registro y un acceso directo al panel. La ventana de
la app muestra el funcionamiento de este Mac:

- el hashrate actual junto al icono en la barra de menús (se puede desactivar),
- el historial de los últimos 15 min / 1 h / 6 h con una línea de tiempo *minando / en pausa / detenido*, el
  hashrate medio y el tiempo en pausa (solo en la memoria de la app; el historial de varios días está en el panel),
- el hashrate por hilo (p. ej. para detectar núcleos de eficiencia más lentos), el ping del pool y los shares
  stratum aceptados/rechazados (no los shares de la sidechain de P2Pool),
- la fuente de alimentación, el nivel de batería y el estado térmico – y, en caso de pausa, el **motivo**: XMRig
  se ejecuta con `--pause-on-battery` y se pausa en cuanto macOS funciona con batería. Esto también ocurre con el
  adaptador conectado cuando un limitador de carga como AlDente deja que la batería se descargue hasta su límite
  inferior; la app detecta limitadores de carga en ejecución y un adaptador conectado y lo indica. También avisa
  del modo de bajo consumo y de la limitación térmica.

El botón *Dashboard* abre `http://<host-del-pool>:8090`; otra dirección se indica en `~/.config/moneta/dashboard`.
Para actualizar: `git pull` y volver a ejecutar `deploy/mac/install.sh` (los ajustes se conservan).

Lo mismo en el terminal:

```bash
MM="$HOME/Library/Application Support/Moneta/moneta-miner.sh"
"$MM" start                  # o stop, restart
"$MM" status
"$MM" threads 3              # o: all – reinicia XMRig si está en marcha
"$MM" autostart on           # o: off
"$MM" log -f
```

Sin el instalador, a mano en primer plano:

```bash
deploy/mac/xmrig-start.sh        # hilos de ~/.config/moneta/threads; si no, todos los núcleos
deploy/mac/xmrig-start.sh 3      # 3 hilos
```

En el primer arranque, macOS pregunta si permitir conexiones entrantes para `xmrig` → **Permitir** (API de XMRig
para el ledger). Prueba desde el NAS:

```bash
curl -s -H "Authorization: Bearer <token>" http://<IP-DEL-EQUIPO>:18000/2/summary | head -c 200
```

Notas:
- Solo conectado a la corriente (`--pause-on-battery`); en portátiles, límite de carga de ~80 % (p. ej. AlDente) y
  superficie dura.
- `MEMORY 98 %` en la salida de XMRig es la caché de macOS; lo que importa es la presión de memoria en el Monitor
  de Actividad.
- "huge pages unavailable" es normal en macOS.
- Windows: Smart App Control bloquea XMRig sin posibilidad de excepción; considera usar WSL2.

## 5. Billetera de minería

```bash
brew install monero
mkdir -p ~/Monero/wallet
monero-wallet-cli --offline --generate-new-wallet ~/Monero/wallet/mining
```

- Escribe las palabras de la semilla en papel (idioma inglés para máxima compatibilidad); nunca las guardes en
  formato digital.
- `set setup-background-mining 0` – de lo contrario la billetera haría que el nodo minara en solitario.
- `address` muestra la dirección principal (`4…`) para `.env`; `viewkey` muestra la clave de visualización
  (secreta) para el ledger.

Saldo y transferencias contra tu propio nodo:

```bash
monero-wallet-cli --wallet-file ~/Monero/wallet/mining --daemon-address <IP-NAS>:18089 --trusted-daemon
```

Comandos útiles: `refresh`, `balance`, `show_transfers`, `transfer <dirección> <importe>`,
`sweep_all <dirección>`, `export_transfers in output=<archivo.csv>`. El XMR minado queda bloqueado ~2 horas
(60 bloques). Registra después cada transferencia en el ledger en **Abgänge** (salidas).
