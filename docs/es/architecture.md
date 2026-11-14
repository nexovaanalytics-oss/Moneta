# Arquitectura

🌐 [Deutsch](../de/architecture.md) · [English](../en/architecture.md) · [Français](../fr/architecture.md) · **Español**

## Componentes

| Componente | Se ejecuta en | Función |
|---|---|---|
| **monerod** (`ghcr.io/sethforprivacy/simple-monerod`) | NAS | Tu propio nodo de Monero, podado (pruned). Verifica cada bloque, entrega plantillas de bloque a P2Pool y datos a la billetera |
| **p2pool** (`ghcr.io/sethforprivacy/p2pool`) | NAS | Pool descentralizado, sidechain **mini**, `--light-mode`. Paga directamente en el bloque de Monero a la dirección de minería |
| **XMRig** | Equipos (macOS/Linux) | Calcula RandomX, se conecta a P2Pool por Stratum; API HTTP de solo lectura para el ledger |
| **wallet-rpc** (`monero-wallet-rpc` en la imagen del ledger) | NAS | Billetera de solo lectura a partir de la dirección + clave de visualización (view key), sincronizada con tu propio nodo |
| **xmr-ledger** (`ghcr.io/nexovaanalytics-oss/xmr-ledger`) | NAS | Entradas, cotizaciones, registro de electricidad, lotes/FIFO, panel, informe Excel |
| **Billetera de minería** (`monero-wallet-cli`) | un equipo | Billetera exclusiva para minar; guarda la semilla sin conexión, la clave de gasto se queda allí |

## Red y puertos

| Puerto | Servicio | Accesible desde |
|---|---|---|
| 18080/tcp | monerod P2P | Internet saliente; entrante solo con redirección de puertos (opcional) |
| 18089/tcp | monerod RPC restringido | LAN (billeteras, P2Pool, wallet-rpc, ledger) |
| 18084/tcp | monerod ZMQ | solo interno de Docker |
| 3333/tcp | P2Pool Stratum | LAN (mineros) |
| 37888/tcp | P2Pool P2P (mini) | Internet saliente |
| 18082/tcp | wallet-rpc | solo interno de Docker, sin puerto publicado |
| 8090/tcp | Panel del ledger | LAN, Basic Auth |
| 18000/tcp | API de XMRig en los equipos | LAN, token Bearer, solo lectura |

**Nunca** expongas Stratum, el RPC ni el panel a Internet mediante redirección de puertos. Si el cortafuegos del
NAS está activo, abre 3333, 8090 y, si hace falta, 18089 solo para tu propia subred local.

## Flujos de datos del ledger

```
                   cada 60 s                         cada 120 s
API de XMRig (equipos) ───▶ miners.py ──▶ power_daily / power_samples
                                         (tiempo de minería × vatios × tarifa, fijados al registrar)
                                         + activity_hourly (valores por hora, solo análisis)
monerod (nodo propio, cada hora) ──▶ network.py ──▶ network_samples (dificultad, recompensa de bloque)

wallet-rpc ──────────────▶ walletsync.py ──▶ inflows  (coinbase = entrada de minería, si no "otra entrada")
                                                │
CoinGecko (cada 10 min,   ──▶ prices.py ──▶ price_points ──▶ cotización por entrada (valor de 5 min más
 últimas 24 h, sin relación                                   cercano, si no diaria, si no manual)
 con los pagos)

Panel (salidas introducidas a mano) ──▶ disposals ──▶ ledger.py: lotes, FIFO, plazos § 23, resumen anual
                                                         └──▶ report.py: Excel / CSV
```

## Archivos en el NAS (ejemplo Synology)

```
/volume1/docker/monero/
├── compose.yaml          # desde deploy/nas/compose.yaml
├── .env                  # XMR_ADDRESS, LEDGER_IMAGE, LEDGER_VERSION (mantener en secreto)
└── ledger/
    ├── data/             # config.toml (¡clave de visualización!), ledger.sqlite, kurse_manuell.csv  → copia de seguridad
    └── wallets/          # archivo de la billetera de solo lectura, se puede recrear en cualquier momento desde la view key
```

La blockchain y los datos de P2Pool están en volúmenes de Docker (`bitmonero`, `p2pool-data`).

## Nota sobre el alojamiento

Muchos proveedores de hosting y de nube prohíben en sus condiciones la minería y la operación de nodos de
blockchain. Ejecuta la pila en casa o revisa antes las condiciones de tu proveedor.
