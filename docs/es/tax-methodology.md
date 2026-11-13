# Metodología fiscal

🌐 [Deutsch](../de/tax-methodology.md) · [English](../en/tax-methodology.md) · [Français](../fr/tax-methodology.md) · **Español**

> **No es asesoramiento fiscal ni jurídico.** Esta página describe cómo calcula el XMR-Ledger y se basa en el
> criterio de la administración tributaria **alemana** (situación a 11/2026). No sustituye el análisis de tu caso
> concreto; en otros países rigen otras normas. La [versión alemana](../de/tax-methodology.md) es la vinculante.

La herramienta aporta cifras y justificantes; la calificación del caso concreto corresponde al contribuyente.
La base es el criterio administrativo recogido en la circular del Ministerio Federal de Hacienda alemán
(BMF-Schreiben) de 6 de marzo de 2025 (IV C 1 - S 2256/00042/064/043, "Einzelfragen zur ertragsteuerrechtlichen
Behandlung bestimmter Kryptowerte", que sustituye a la circular de 10 de mayo de 2022; creación de bloques:
n.º marg. 35 y ss.).

## Entradas (ingresos)

- Los rendimientos de la creación de bloques son, según las circunstancias, rendimientos de actividades
  económicas (§ 15 EStG) u otros ingresos por prestaciones (§ 22 n.º 3 EStG); esto también se aplica a los
  criptoactivos recibidos de pools de minería.
- Se valoran al **precio de mercado en el momento de la recepción** (de forma simplificada: al abonarse en la
  billetera).
- Implementación: momento = hora del bloque de la transacción coinbase; cotización = cotización de CoinGecko de
  5 minutos más cercana (máx. 15 min de diferencia), si no la cotización diaria a las 00:00 UTC, si no manual. La
  fuente se guarda para cada entrada.
- Importe en EUR redondeado al céntimo por entrada y después sumado.
- Solo cuentan las entradas coinbase; las demás entradas (p. ej. el cambio de tus propias transferencias) se
  listan pero no se cuentan como ingreso.

## Gastos: electricidad (Werbungskosten / Betriebsausgaben)

- **Consumo adicional** medido por equipo × **tiempo de minería** registrado automáticamente × **precio de la
  electricidad**.
- Medición: `powermetrics` carga − reposo, +10 % de pérdidas de la fuente, redondeado al alza por la RAM; la
  fecha y el método constan en `config.toml` (`note`) y en el informe (hoja **Geräte**, equipos).
- Los vatios y la tarifa se fijan en cada registro; los cambios posteriores solo surten efecto hacia el futuro.
- Opcional: consumo adicional del NAS (`nas_extra_watts`); actualmente 0, ya que el NAS funciona de todos modos.
- No incluido: amortización del hardware existente (los equipos también se usan de forma privada).

## Límite exento del § 22 n.º 3 EStG

El informe comprueba si el resultado (ingresos − electricidad) es **inferior a 256 €**. Este límite (Freigrenze,
no una reducción: si se alcanza, tributa el importe íntegro) se aplica al conjunto de ingresos por prestaciones
del año. Las pérdidas solo pueden compensarse con ingresos del § 22 n.º 3 (§ 22 n.º 3, frases 3 y 4 EStG, con
aplicación análoga del § 10d). Si el resultado es negativo de forma permanente, la intención de obtener
beneficios debe valorarse por separado.

## Transmisión (§ 23, apdo. 1, frase 1, n.º 2 EStG)

- Cada pago se considera una **adquisición**; coste de adquisición = valor en el momento de la recepción.
- Orden de salida **FIFO** por billetera (la billetera de minería).
- **Plazo de tenencia de un año:** "exento desde" (steuerfrei ab) = el día siguiente al vencimiento de un año
  desde la recepción (§§ 187, apdo. 1, 188, apdo. 2 BGB; 29/02 → 01/03).
- La permuta por otros criptoactivos y el pago con XMR también son transmisiones; ingreso = valor en EUR de lo
  recibido.
- El traspaso a una billetera propia no es una transmisión; los lotes (coste de adquisición, fecha) figuran en el
  informe para poder continuarlos en la billetera de destino.
- Límite exento de **1000 €** (§ 23, apdo. 3, frase 5 EStG) para el conjunto de operaciones privadas de
  transmisión del año.

## Justificantes

- Informe anual en Excel (con la versión del ledger que lo generó), CSV de las entradas.
- Exportación de la billetera: `export_transfers in output=…` en `monero-wallet-cli`.
- Prueba de P2Pool: mini.p2pool.observer (introducir la dirección).
- Acreditación del origen de los fondos ante bancos y plataformas: dirección de minería, pagos, costes de
  electricidad.

## Regulación

A partir del **10 de julio de 2027** (Reglamento europeo contra el blanqueo de capitales, Reglamento (UE)
2024/1624, art. 79), los proveedores de servicios de criptoactivos regulados en la UE ya no podrán mantener
cuentas con "privacy coins" como Monero. Mantenerlo en una billetera propia y minar siguen estando permitidos;
convertirlo a euros solo sería posible en dos pasos (XMR → BTC de forma descentralizada y después una plataforma
regulada).

## Otros países

Por ahora, el ledger solo aplica las normas alemanas. Los perfiles fiscales para otros países (plazos de
tenencia, límites, métodos de coste de adquisición) están en la [hoja de ruta](../../ROADMAP.md); las
aportaciones de personas que conozcan las normas de su país son muy bienvenidas.
