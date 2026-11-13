# Decisiones de diseño

🌐 [Deutsch](../de/design-decisions.md) · [English](../en/design-decisions.md) · [Français](../fr/design-decisions.md) · **Español**

Por qué Moneta está construido así. Añadir las nuevas entradas arriba (fecha, contexto, decisión,
consecuencias). La [versión alemana](../de/design-decisions.md) es la de referencia.

### D-08 · 13/11/2026 – Multilingüe y abierto a contribuciones
Moneta debe poder usarse más allá de los países germanohablantes e invitar a participar. El idioma del proyecto
para los archivos de la comunidad (README, CONTRIBUTING, CHANGELOG, SECURITY, plantillas) es el inglés; el README,
la guía de contribución y el código de conducta también están en alemán, francés y español. La documentación
está en `docs/<de|en|fr|es>/` con nombres de archivo idénticos; si hay diferencias, prevalece la versión alemana,
en especial para la metodología fiscal, que describe el derecho alemán. El panel y el informe Excel siguen por
ahora en alemán; su traducción encabeza la [hoja de ruta](../../ROADMAP.md). Código de conducta: Contributor
Covenant 3.0.

### D-07 · 13/11/2026 – Publicación bajo EUPL-1.2
Un copyleft que también cubre la operación como servicio web; versiones oficiales en todas las lenguas de la UE;
responsabilidad y ley aplicable según el derecho de la UE. Licencias de terceros en
[`THIRD_PARTY.md`](../../THIRD_PARTY.md), licencia de Monero dentro de la imagen.

### D-06 · 13/11/2026 – Imagen construida con GitHub Actions, versión fijada a conciencia en el servidor
GitHub Actions prueba y construye `ghcr.io/nexovaanalytics-oss/xmr-ledger`. En el servidor, la versión se fija en
`.env` (`LEDGER_VERSION`), sin actualización automática. Cada informe Excel indica la versión que lo generó.

### D-05 · 13/11/2026 – Cotizaciones asignadas localmente desde un historial de 5 minutos
Consultas del tipo "cotización en el momento X" revelarían al proveedor de cotizaciones los momentos de pago;
junto con la dirección pública de P2Pool, la IP podría vincularse a la dirección de minería. Por eso se descargan
a intervalos fijos (actualmente cada 10 minutos) las últimas 24 h y se guardan localmente; la asignación se hace en local (máx. 15 min de
diferencia). La cotización diaria es solo un respaldo, y en ese caso solo se transmite la fecha.

### D-04 · 11/11/2026 – Coste eléctrico = consumo adicional medido × tiempo de minería registrado
En un portátil, un enchufe medidor también registra la carga y el uso normal. Por eso el consumo adicional se
mide una vez (carga − reposo, +10 % por la fuente) y el tiempo de funcionamiento se registra automáticamente a
través de la API de XMRig. Los vatios y la tarifa se fijan en cada registro; los cambios de configuración solo
surten efecto hacia el futuro.

### D-03 · 11/11/2026 – Billetera de solo lectura, salidas introducidas a mano
La clave de gasto no debe estar en el servidor. `monero-wallet-rpc` trabaja con la dirección + la clave de
visualización. Una billetera así ve las entradas pero no las salidas: solo las entradas coinbase cuentan como
entradas de minería, las demás (p. ej. el cambio) se listan por separado y las salidas se registran en el panel.

### D-02 · 11/11/2026 – Un lote por pago, FIFO
Cada pago es una adquisición (coste de adquisición = valor en la recepción); orden de salida FIFO; "exento desde"
= el día siguiente al vencimiento del plazo de un año (§§ 187, apdo. 1, 188, apdo. 2 BGB). Detalles:
[Metodología fiscal](tax-methodology.md).

### D-01 · 11/11/2026 – Nodo propio + P2Pool en el NAS, los equipos solo calculan
El nodo y el pool necesitan almacenamiento pero casi nada de potencia de cálculo, y el NAS funciona de todos
modos. monerod podado con `--sync-pruned-blocks`, P2Pool mini con `--light-mode`. Los equipos solo se conectan
por Stratum; pueden sumarse tantos equipos adicionales como se quiera.
