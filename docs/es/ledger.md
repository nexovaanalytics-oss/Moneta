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
| `[power]` | `poll_seconds`, `nas_extra_watts` (0 = no contabilizar el NAS), `[[power.tariff]]` con `valid_from`, `ct_per_kwh` |
| `[[miner]]` | por equipo: `name`, `url` (`http://IP:18000`), `token`, `watts` (consumo adicional), `note` (medición) |

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
| **Zuflüsse** (entradas) | Todos los pagos con cotización y fuente; otras entradas por separado |
| **Strom** (electricidad) | Horas de minería, vatios medios, kWh, ct/kWh medios, coste por equipo y mes, más totales de todos los equipos (año y por mes) |
| **Auswertung** (análisis) | Periodo a elección (preajustes: última noche, 24 h, 7/30 días, mes, año): por equipo, tiempo minando/en pausa/inaccesible con línea de tiempo, hashrate medio/máx., hashes, kWh, coste; valor esperado (hashes ÷ dificultad × recompensa de bloque) frente a pagos reales; por día; CSV |
| **Lose** (lotes) | Lotes FIFO con coste de adquisición y fecha **steuerfrei ab** (exento desde) |
| **Abgänge** (salidas) | Registrar/borrar transferencias desde la billetera de minería |
| **Verkaufs-Rechner** (calculadora de venta) | Simular una venta/permuta prevista (no se guarda nada) |

`/health` responde `ok` sin contraseña (healthcheck de Docker).

**Actualización:** mientras la pestaña está abierta, el resumen obtiene valores nuevos cada 30 s sin recargar la
página (`/api/live`, JSON, mismo inicio de sesión; en pausa en una pestaña en segundo plano). Junto al año indica
la antigüedad de la última consulta, o «Verbindung verloren» (conexión perdida). Sin JavaScript, el resumen se
recarga cada 2 minutos. Los datos los recoge el propio ledger en segundo plano: equipos cada `poll_seconds`
(60 s por defecto), billetera cada 120 s, historial de cotizaciones cada 10 minutos.

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
| `activity.py` | Valores por hora por equipo, análisis por periodos |
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
- CoinGecko (gratuito, sin garantía); con la API gratuita, las cotizaciones históricas solo llegan a
  aproximadamente un año atrás.
- El tiempo de minería solo cuenta mientras el ledger está en marcha y alcanza el equipo (los costes tienden a
  quedarse cortos antes que a exagerarse).
- La calculadora de venta no descuenta las comisiones de red.
- Panel por HTTP: la contraseña viaja sin cifrar dentro de la LAN (HTTPS mediante proxy inverso está en la
  [hoja de ruta](../../ROADMAP.md)).
- La lógica fiscal aplica las normas **alemanas** (ver [Metodología fiscal](tax-methodology.md)); los perfiles
  para otros países están en la hoja de ruta.
