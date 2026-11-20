# XMR-Ledger

🌐 [Deutsch](../de/ledger.md) · [English](../en/ledger.md) · [Français](../fr/ledger.md) · **Español**

Documenta automáticamente tu minería de Monero: entradas con cotización, costes de electricidad, lotes FIFO,
plazos de tenencia; además de un panel, un informe anual en Excel y una calculadora de venta.
Método y base legal: [Metodología fiscal](tax-methodology.md).

> El panel y el informe Excel están por ahora **solo en alemán**. Abajo se indican en negrita las etiquetas
> alemanas de la interfaz con su traducción. Traducir la interfaz encabeza la [hoja de ruta](../../ROADMAP.md):
> ¡toda ayuda es bienvenida!

## Configuración

`ledger/data/config.toml` en el NAS (plantilla: [`ledger/config.example.toml`](../../ledger/config.example.toml),
comentarios en alemán). Contiene la **clave de visualización**: no la compartas y nunca la subas al repositorio.

| Sección | Campos |
|---|---|
| `[wallet]` | `address` (4…), `view_key` (`viewkey` → secret), `restore_height` (altura de bloque poco antes de crear la billetera), `wallet_password` (libre) |
| `[web]` | `port`, `user`, `password` (obligatorio) |
| `[prices]` | `coingecko_api_key` (opcional; una clave demo gratuita eleva el límite de consultas) |
| `[node]` | `rpc_url` de tu propio nodo para dificultad y recompensa de bloque (por defecto `http://monerod:18089/json_rpc`, vacío = desactivado) |
| `[pool]` | para equipos nuevos: `stratum_host` (vacío = IP del NAS), `stratum_port` (por defecto 3333); `pairing` (por defecto `true`) permite el emparejamiento con código; `log` (log de P2Pool, por defecto `/p2pool/p2pool.log`) y `sidechain` (`mini`, `nano`, `main`) para [Pago → equipo](#pago--equipo) |
| `[power]` | `poll_seconds`, `nas_extra_watts` (0 = no contabilizar el NAS), `[[power.tariff]]` con `valid_from`, `ct_per_kwh` |
| `[[miner]]` | opcional, en lugar del emparejamiento en el panel, por equipo: `name`, `url` (`http://IP:18000`), `token`, `watts` (consumo adicional), `note` (medición) |

Comprobar antes de copiar:

```bash
python3 -c "import tomllib; c=tomllib.load(open('config.toml','rb')); print(len(c['wallet']['address']), len(c['miner']))"
```

Tras cambios: `sudo docker restart xmr-ledger`.

## Panel

`http://<IP-NAS>:8090` (Basic Auth, solo LAN).

| Página | Contenido |
|---|---|
| **Übersicht** (resumen) | Saldo, importe vendible libre de impuestos, ingresos/electricidad/resultado del año, estado de los equipos con fila de total (hashrate y consumo adicional de todos los equipos minando, incl. NAS si está configurado), últimos pagos, descargas |
| **Zuflüsse** (entradas) | Todos los pagos con cotización, fuente y «Verursacht von» (parte por equipo), tabla «Je Rechner» del año; otras entradas por separado |
| **Strom** (electricidad) | Horas de minería, vatios medios, kWh, ct/kWh medios, coste por equipo y mes, más totales de todos los equipos (año y por mes) |
| **Auswertung** (análisis) | Periodo a elección (preajustes: última noche, 24 h, 7/30 días, mes, año): por equipo, tiempo minando/en pausa/inaccesible con línea de tiempo, hashrate medio/máx., hashes, kWh, coste, shares y XMR atribuidos; valor esperado (hashes ÷ dificultad × recompensa de bloque) frente a pagos reales; línea de tiempo «Shares und Auszahlungen» con «Verursacht von»; por día; CSV |
| **Lose** (lotes) | Lotes FIFO con coste de adquisición y fecha **steuerfrei ab** (exento desde) |
| **Abgänge** (salidas) | Registrar/borrar transferencias desde la billetera de minería |
| **Verkaufs-Rechner** (calculadora de venta) | Simular una venta/permuta prevista (no se guarda nada) |
| **Geräte** (equipos) | Emparejar equipos nuevos con un código y aprobarlos, cambiar el consumo adicional «a partir de ahora» (historial), retirar |

`/health` responde `ok` sin contraseña (healthcheck de Docker).

`/api/moneta` también responde sin contraseña, pero solo con el nombre del servicio, la versión, la dirección
stratum y si el emparejamiento es posible: así encuentran los equipos nuevos el ledger en la red doméstica.
En `economics` devuelve además los valores para elegir los hilos al medir: dificultad y recompensa de bloque de tu
propio nodo, la última cotización local (de 2 horas como máximo) y la tarifa actual, y con ello el rendimiento por
H/s y el coste eléctrico por vatio y día (`null` mientras falten el valor del nodo o la cotización).
`/api/pair` (código de emparejamiento) y `/api/heartbeat` (token del equipo) solo aceptan JSON de los equipos,
consulta [Emparejar equipos](#emparejar-equipos).

**Actualización:** mientras la pestaña está abierta, el resumen obtiene valores nuevos cada 30 s sin recargar la
página (`/api/live`, JSON, mismo inicio de sesión; en pausa en una pestaña en segundo plano). Junto al año indica
la antigüedad de la última consulta, o «Verbindung verloren» (conexión perdida). Sin JavaScript, el resumen se
recarga cada 2 minutos. Los datos los recoge el propio ledger en segundo plano: equipos cada `poll_seconds`
(60 s por defecto), billetera cada 120 s, historial de cotizaciones cada 10 minutos.

## Emparejar equipos

Los equipos nuevos pueden añadirse sin una entrada en `config.toml`:

1. Panel → **Geräte** → «Neuen Rechner koppeln – Code erzeugen». El código de 6 cifras es válido 10 minutos y una
   sola vez; tras cinco intentos fallidos deja de ser válido.
2. El equipo se registra con el código mediante `POST /api/pair`: nombre, URL de XMRig (solo direcciones de la red
   doméstica), token de la API, perfil del equipo (modelo, núcleos) y, si se ha medido, una propuesta de hilos y
   de consumo adicional. El instalador y la app de la barra de menús lo harán con la próxima actualización de
   `deploy/mac`.
3. El equipo aparece en **Wartet auf Freigabe** (pendiente de aprobación). Comprueba o introduce el consumo
   adicional y la nota de medición y pulsa **Freigeben** (aprobar). Solo a partir de entonces se consulta; el valor
   se fija en cada registro, igual que con `[[miner]]`.
4. Si cambia el consumo adicional (p. ej. otro número de hilos), guarda un valor nuevo en **Aktive Rechner**: se
   aplica desde que se guarda; los registros anteriores no cambian. El informe de Excel (hoja «Geräte») muestra el
   historial con «gültig ab» (válido desde). **Stilllegen** (retirar) detiene las consultas; el historial y el
   nombre siguen visibles.

Los equipos emparejados se notifican con su token mediante `POST /api/heartbeat`; una IP cambiada se adopta.
Los equipos de `[[miner]]` siguen funcionando igual (los cambios ahí siguen requiriendo reiniciar el contenedor).

## Pago → equipo

P2Pool paga según PPLNS: un pago se reparte entre todas las shares de la ventana de los últimos 2160 bloques de la
sidechain (mini ≈ 6 h, nano ≈ 18 h), ponderadas por su dificultad. Por eso el ledger muestra para cada pago qué
equipos propios participaron y con qué parte: en **Zuflüsse** («Verursacht von», tabla «Je Rechner») y en
**Auswertung** (línea de tiempo «Shares und Auszahlungen», columnas «Shares» y «zugeordnet XMR»).

- **exakt** (exacto): a partir del log de P2Pool. Cada share propia aparece con hora, dificultad y dirección del
  cliente (`SHARE FOUND: … client <IP:puerto>[, user <nombre>]`), cada pago con la altura del bloque. El ledger lee
  el log de forma continua cada 60 s (tablas `p2pool_shares`, `p2pool_payouts`). El ledger reconoce el equipo de
  una share por el login de XMRig: el instalador de `deploy/mac` configura XMRig con el
  nombre del equipo como login (`-u <nombre>`, guardado en `~/.config/moneta/name`, tomado del ledger en los equipos
  emparejados). Si no, cuenta la IP del cliente de `[[miner]]` o del emparejamiento.
- **eindeutig** (inequívoco): login `x` y una dirección que no pertenece a ningún equipo; es lo típico cuando
  P2Pool, en la red de Docker, solo ve la dirección de la pasarela. Entonces deciden los tiempos de minería del
  ledger: si en el momento de la share (± dos consultas, por horas pasados 30 días) solo minaba un equipo, es suya.
  El resultado se guarda por share. Requisito: todos los equipos del pool están registrados en el ledger.
- **teilweise** (parcial): el log empieza dentro de la ventana de este pago.
- **geschätzt** (estimado): si en el momento de una share minaban varios equipos, se reparte según su hashrate en
  ese instante (rombo hueco en el gráfico). Sin shares del log (falta el log o empieza más tarde), el reparto sigue
  la parte de hashes en toda la ventana. Ningún equipo minando según el ledger: «unbekannt».

**Activar:** el servicio `ledger` recibe el volumen de P2Pool en solo lectura (`deploy/nas/compose.yaml`):

```yaml
    volumes:
      - ./ledger/data:/data
      - p2pool-data:/p2pool:ro
```

Después sustituye `compose.yaml` en el NAS y ejecuta `sudo docker compose -p monero-pool up -d`. Sin el volumen
todo sigue funcionando como antes, solo «geschätzt». **Historial:** P2Pool no rota su log por sí mismo; mientras
no se haya borrado `p2pool.log`, el ledger lee todo el historial en el primer arranque y atribuye también los pagos
anteriores de forma exacta.

Solo visualización: entradas, cotizaciones, informe y tratamiento fiscal no cambian; a efectos fiscales sigue
contando el pago completo. No se consultan servicios externos como p2pool.observer, porque eso vincularía la
dirección de minería con tu IP.

## Uso

- **Salidas:** una billetera de solo lectura no ve las transferencias salientes. Registra cada transferencia:
  cantidad = importe enviado a terceros + comisión de red (sin contar el cambio); tipo venta/permuta, pago o
  traspaso a una billetera propia; en venta/permuta/pago, el contravalor en EUR.
- **Cotización ausente o incorrecta:** `ledger/data/kurse_manuell.csv`, una línea por registro, `TXID;cotización`
  o `AAAA-MM-DD;cotización` (se admite coma decimal). Solo se aplica a entradas sin cotización guardada.
- **Cambia el precio de la electricidad:** añade un nuevo bloque `[[power.tariff]]` con `valid_from` y reinicia el
  contenedor.
- **Informe anual:** Übersicht → **Excel-Bericht** (hojas: resumen con límites exentos, entradas, electricidad,
  equipos, lotes, salidas, otras entradas). El resumen indica la versión del ledger que lo generó.

## Estructura del código (`ledger/app/`)

| Módulo | Función |
|---|---|
| `main.py` | Arranque, hilos, señales |
| `config.py` | Leer y validar `config.toml` |
| `db.py` | SQLite, migraciones (`PRAGMA user_version`), conexiones por hilo |
| `walletsync.py` | wallet-rpc: crear/abrir la billetera, leer entradas, limpiar tras reorganizaciones |
| `prices.py` | Historial de cotizaciones de 5 minutos, asignación de cotizaciones, respaldo con cotización diaria, cotizaciones manuales |
| `miners.py` | Consultar la API de XMRig, registrar tiempo de minería y costes |
| `devices.py` | Equipos emparejados: código de emparejamiento, registro, aprobación, historial de vatios, heartbeat |
| `activity.py` | Valores por hora por equipo, análisis por periodos |
| `shares.py` | Leer el log de P2Pool, atribuir pagos a los equipos (solo visualización) |
| `network.py` | Dificultad y recompensa de bloque desde tu propio nodo |
| `ledger.py` | Lotes, FIFO, plazos, resumen anual, calculadora de venta |
| `report.py` | Exportación a Excel y CSV |
| `web.py` | Panel, formularios, descargas, autenticación, protección CSRF |
| `version.py` | Información de versión a partir de los argumentos de build |

Pruebas: `python -m pytest -q ledger/tests` (billetera, XMRig y cotizaciones simulados; no hace falta Internet).

## Limitaciones

- Análisis: los valores por minuto (con línea de tiempo) se conservan 30 días, después valores por hora. Hashes =
  hashrate informado × intervalo de consulta (aproximación); el valor esperado ignora uncles/huérfanos. Solo
  visualización, no es base fiscal.
- Pago → equipo: la ventana se basa en el tiempo (2160 × tiempo de bloque) y por tanto aproxima la ventana PPLNS;
  no se tienen en cuenta los uncles. Detrás del proxy de puertos de Docker, P2Pool solo ve la
  dirección de la pasarela; entonces cuenta el login de XMRig. Las shares anteriores se atribuyen por los tiempos
  de minería.
- CoinGecko (gratuito, sin garantía); con la API gratuita, las cotizaciones históricas solo llegan a
  aproximadamente un año atrás.
- El tiempo de minería solo cuenta mientras el ledger está en marcha y alcanza el equipo (los costes tienden a
  quedarse cortos antes que a exagerarse).
- La calculadora de venta no descuenta las comisiones de red.
- Panel por HTTP: la contraseña viaja sin cifrar dentro de la LAN (HTTPS mediante proxy inverso está en la
  [hoja de ruta](../../ROADMAP.md)).
- La lógica fiscal aplica las normas **alemanas** (ver [Metodología fiscal](tax-methodology.md)); los perfiles
  para otros países están en la hoja de ruta.
- Emparejamiento: el token y los datos del equipo viajan sin cifrar por la LAN, igual que la contraseña del
  panel. Sin un código válido ningún equipo puede registrarse, y sin aprobación ninguno se registra.
