# Moneta

**Acuña tus propios Monero en casa.**
Tu NAS ejecuta el nodo y P2Pool, tus MacBook calculan, y el XMR-Ledger lleva una contabilidad de cada pago lista
para Hacienda.

🌐 [English](README.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · **Español**

[![Licencia: EUPL-1.2](https://img.shields.io/badge/license-EUPL--1.2-blue.svg)](LICENSE)
[![ledger CI](https://github.com/nexovaanalytics-oss/Moneta/actions/workflows/ledger.yml/badge.svg)](https://github.com/nexovaanalytics-oss/Moneta/actions/workflows/ledger.yml)
[![Docs: DE · EN · FR · ES](https://img.shields.io/badge/docs-DE%20%C2%B7%20EN%20%C2%B7%20FR%20%C2%B7%20ES-informational.svg)](docs/README.md)
[![Contribuciones bienvenidas](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.es.md)

> Lleva el nombre de Juno Moneta, cuyo templo en el Capitolio de Roma albergaba la ceca de la ciudad: de ahí
> "money", "moneda" y, a través del esperanto, "Monero".

```
Equipo 1 (p. ej. MacBook Pro) ─┐                         NAS (p. ej. Synology DS920+)
Equipo 2 (p. ej. MacBook Air) ─┼── XMRig ── Stratum ──▶ p2pool (mini) ──▶ monerod (pruned) ──▶ red Monero
                               │                                             ▲
                               └── API XMRig ◀── xmr-ledger ── wallet-rpc ───┘
                                                     │  (view key, solo lectura)
                                                Panel :8090 · informe anual Excel
```

## ¿Por qué Moneta?

- **Sin intermediarios.** Tu propio nodo más P2Pool: sin operador de pool, sin cuenta, sin comisión de pool. Los
  pagos llegan directamente a tu billetera dentro de los bloques de Monero que encuentra el pool.
- **Hardware que ya tienes.** Un NAS que funciona de todos modos y los portátiles de tu escritorio.
- **Privacidad desde el diseño.** El servidor solo recibe una billetera de solo lectura: la clave de gasto nunca
  sale de tu equipo. Las consultas de cotización nunca revelan cuándo recibiste un pago.
- **Cuentas que cuadran.** Cada pago con su cotización en EUR en el momento de la recepción, coste eléctrico a
  partir de los vatios medidos × el tiempo de minería registrado, lotes FIFO con fechas de tenencia y un informe
  anual en Excel.
- **Números honestos.** Con los precios habituales de la electricidad en Europa, minar en casa es un hobby, no
  una inversión; Moneta te muestra exactamente lo que cuesta y lo que aporta.

## XMR-Ledger

- **Entradas:** cada pago de P2Pool mediante una billetera de solo lectura (view key) en tu propio nodo
- **Cotización en el momento de la recepción** a partir de un historial de cotizaciones de 5 minutos guardado en
  local: el proveedor nunca conoce tus momentos de pago
- **Costes de electricidad** = consumo adicional medido × tiempo de minería registrado automáticamente
- **Lotes FIFO** con coste de adquisición y fecha "exento desde" (§ 23 EStG alemán)
- **Panel**, **informe anual en Excel** (con comprobación de límites exentos), **calculadora de venta**
- Python 3.12, solo biblioteca estándar + openpyxl; imagen `ghcr.io/nexovaanalytics-oss/xmr-ledger`

El panel y el informe Excel están por ahora **en alemán**; la documentación está disponible en cuatro idiomas.
La lógica fiscal aplica las normas **alemanas**; consulta la hoja de ruta para otros países.

## Contenido del repositorio

| Carpeta | Contenido |
|---|---|
| [`ledger/`](ledger/) | XMR-Ledger: aplicación Python, Dockerfile, pruebas |
| [`deploy/nas/`](deploy/nas/) | `compose.yaml` y `.env.example` para la pila del NAS |
| [`deploy/mac/`](deploy/mac/) | Script de arranque de XMRig, medición del consumo |
| [`docs/`](docs/README.md) | Documentación en alemán, inglés, francés y español |

## Documentación

- [Arquitectura](docs/es/architecture.md): componentes, puertos, flujos de datos
- [Instalación NAS](docs/es/setup-nas.md) · [Instalación equipo (macOS)](docs/es/setup-mac.md)
- [Usar el XMR-Ledger](docs/es/ledger.md) · [Metodología fiscal](docs/es/tax-methodology.md)
- [Operación: actualizaciones, versiones, copias de seguridad, solución de problemas](docs/es/operations.md)
- [Decisiones de diseño](docs/es/design-decisions.md)

## Inicio rápido

1. Crear una billetera de minería y anotar la dirección principal y la clave de visualización ([instalación equipo](docs/es/setup-mac.md#5-billetera-de-minería))
2. En el NAS, crear `compose.yaml`, `.env` y `ledger/data/config.toml` y arrancar ([instalación NAS](docs/es/setup-nas.md))
3. Dejar que el nodo se sincronice (varios días) y después iniciar XMRig con `deploy/mac/xmrig-start.sh`
4. Panel en `http://<IP-NAS>:8090`

Desarrollo: `pip install -r ledger/requirements.txt pytest && python -m pytest -q ledger/tests`

## 🤝 ¡Participa!

Moneta nació como proyecto de hobby y ahora está abierto a todo el mundo. Tanto si minas con una Raspberry Pi,
como si conoces las normas fiscales de España, México o Argentina, o simplemente has encontrado una errata: eres
bienvenido. Issues y pull requests en **español, inglés, alemán o francés**.

Buenos puntos de partida:

- 🌍 **Traducir el panel y el informe Excel** (EN/FR/ES y más)
- 🧾 **Añadir un perfil fiscal para tu país**
- 📊 **Compartir hashrate y consumo** de tu equipo: un formulario de issue, sin código
- 🐧 **Guías** para Linux, Windows (WSL2) y otros NAS
- 🧩 **Imagen arm64** para Raspberry Pi y NAS ARM

→ [Hoja de ruta](ROADMAP.md) · [Guía de contribución](CONTRIBUTING.es.md) ·
[Good first issues](https://github.com/nexovaanalytics-oss/Moneta/labels/good%20first%20issue) ·
[Código de conducta](CODE_OF_CONDUCT.es.md)

## Avisos importantes

- **No es asesoramiento fiscal ni jurídico.** El ledger aplica el criterio de la administración tributaria
  alemana (circular del BMF de 6 de marzo de 2025); la calificación de tu caso concreto te corresponde a ti y a
  tu asesor.
- **Sin garantía** sobre cotizaciones, cálculos e informes: revisa los resultados antes de usarlos.
- **Rentabilidad:** con los precios habituales de la electricidad en Europa, minar en casa es sobre todo un
  hobby, no una inversión.
- **Regulación:** a partir del 10 de julio de 2027, los proveedores de servicios de criptoactivos regulados en la
  UE ya no podrán ofrecer "privacy coins" como Monero (AMLR). Comprueba las normas que te aplican.
- **Alojamiento:** muchos proveedores prohíben la minería y los nodos de blockchain; ejecútalo en casa o revisa
  sus condiciones.
- Informa de fallos de seguridad de forma confidencial: [SECURITY.md](SECURITY.md).

## Licencia

Copyright © 2026 colaboradores de Moneta.
Con licencia **European Union Public Licence v. 1.2** ([LICENSE](LICENSE), SPDX: `EUPL-1.2`).
Versiones oficiales en todas las lenguas de la UE, también en español:
https://interoperable-europe.ec.europa.eu/collection/eupl/eupl-text-eupl-12
Software de terceros y fuentes de datos: [THIRD_PARTY.md](THIRD_PARTY.md).
