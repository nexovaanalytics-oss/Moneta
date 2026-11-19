# Decisiones de diseño

🌐 [Deutsch](../de/design-decisions.md) · [English](../en/design-decisions.md) · [Français](../fr/design-decisions.md) · **Español**

Por qué Moneta está construido así. Añadir las nuevas entradas arriba (fecha, contexto, decisión,
consecuencias). La [versión alemana](../de/design-decisions.md) es la de referencia.

### D-12 · 19.11.2026 – Atribuir pagos a los equipos: log propio de P2Pool en lugar de servicios externos
Con varios equipos no está claro cuál «causó» un pago. Según PPLNS, un pago se reparte entre todas las shares
propias de la ventana; qué equipo encontró una share solo consta en el log de tu propio P2Pool (dirección del
cliente y, opcionalmente, el nombre de login). Por eso el ledger monta el volumen de P2Pool en solo lectura y lee
el log de forma continua. Se descartan servicios públicos como p2pool.observer: no conocen los equipos, y cada
consulta vincularía la dirección de minería con tu IP. Sin log, el reparto se estima según la parte de hashes y se
marca como tal. La atribución es solo visualización; entradas, cotizaciones e informe no cambian, y a efectos
fiscales cuenta el pago completo.

### D-11 · 14.11.2026 – Elegir los hilos por utilidad marginal en lugar de una regla general
La regla «sin ventilador: núcleos de rendimiento − 1» procede de un M1 e ignora los núcleos de eficiencia; en un M4
(4 + 6 núcleos) quedaban seis núcleos sin probar. Por eso `einmessen.sh` mide escalones hasta todos los núcleos y
propone el escalón con el mejor saldo entre rendimiento calculado y coste eléctrico. El ledger aporta los valores
en `economics` de `GET /api/moneta` a partir de datos que ya tiene (dificultad del propio nodo, cotización local,
tarifa), sin consultas a Internet y sin relación con pagos individuales. Así, la cotización y la tarifa pueden
leerse en la red local sin contraseña; la elección de hilos lo necesita, porque un equipo nuevo no tiene token
antes del emparejamiento. Sin esos valores sigue valiendo el mejor hashrate por vatio. El cálculo solo sirve para
elegir los hilos y no se guarda.

### D-10 · 14/11/2026 – Emparejar equipos nuevos con un código, aprobación en el panel
Los equipos nuevos deben poder añadirse sin editar `config.toml` a mano. El ledger hace de punto central: responde
sin contraseña a `GET /api/moneta` (solo servicio, versión y dirección stratum) para que el instalador y la app lo
encuentren en la red doméstica; Bonjour/mDNS queda descartado porque el contenedor no puede hacer multicast desde la
red bridge. El emparejamiento usa un código de 6 cifras del panel (10 minutos, de un solo uso, inválido tras cinco
intentos fallidos) mediante `POST /api/pair`. Como no es un formulario del navegador, el código, cuerpos solo JSON
y un límite de tamaño sustituyen ahí la comprobación same-origin; `/api/heartbeat` comprueba el token del equipo.
Un equipo emparejado solo se consulta tras aprobarlo con un consumo adicional medido; de lo contrario, cualquier
dispositivo de la LAN podría escribir costes de electricidad en los datos con relevancia fiscal. Los vatios se
guardan como historial con `valid_from` y nunca se sobrescriben; `[[miner]]` en `config.toml` sigue siendo posible.

### D-09 · 13/11/2026 – Inicio del minero desde una app de la barra de menús, compilada localmente en lugar de distribuida firmada
Los equipos deben poder configurarse sin conocimientos de terminal e iniciarse con un botón. Un instalador
(`deploy/mac/install.sh`) configura XMRig como agente de launchd y compila la app de la barra de menús desde el
código fuente en el propio equipo (`swiftc` de las Command Line Tools, que Homebrew necesita de todos modos). Los
programas compilados localmente no llevan atributo de cuarentena, así que Gatekeeper no pregunta y no hacen falta
ni una cuenta de desarrollador de Apple de pago ni la notarización. XMRig no se incluye, sino que se instala con
Homebrew (actualizaciones propias); la app solo controla el agente y lee la API local de XMRig. La
entrada `[[miner]]` en `config.toml` sigue siendo a propósito un paso manual: los vatios se fijan en cada registro
y deben medirse antes. Una app firmada y notarizada para descargar queda como opción para más adelante.

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
