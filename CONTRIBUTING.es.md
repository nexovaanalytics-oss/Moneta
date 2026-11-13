# Contribuir a Moneta

🌐 [English](CONTRIBUTING.md) · [Deutsch](CONTRIBUTING.de.md) · [Français](CONTRIBUTING.fr.md) · **Español**

¡Gracias por querer ayudar! Moneta es un pequeño proyecto de hobby y cada aportación cuenta: una medición de tu
equipo, una traducción, un informe de error o un pull request. Puedes escribir issues y pull requests en
**español, inglés, alemán o francés**.

Al participar aceptas nuestro [código de conducta](CODE_OF_CONDUCT.es.md).

## Formas de contribuir

| Tienes … | Podrías … |
|---|---|
| 10 minutos | Compartir el hashrate y el consumo de tu equipo (formulario de issue "Device measurement") |
| una hora | Corregir una errata, mejorar una guía, actualizar una traducción |
| una tarde | Escribir una guía (Linux, Windows/WSL2, QNAP, Unraid, TrueNAS …), tomar un [good first issue](https://github.com/nexovaanalytics-oss/Moneta/labels/good%20first%20issue) |
| más tiempo | Traducir el panel y el informe, añadir un perfil fiscal para tu país, construir la imagen arm64; consulta la [hoja de ruta](ROADMAP.md) |

Las ideas y preguntas también son bienvenidas, como issue o en las Discussions.

## Antes de empezar

- Revisa los [issues](https://github.com/nexovaanalytics-oss/Moneta/issues) y la [hoja de ruta](ROADMAP.md):
  quizá alguien ya esté trabajando en ello.
- Para cambios grandes, abre primero un issue describiendo tu plan. Así todos ahorramos tiempo.
- Lee la [arquitectura](docs/es/architecture.md) y las [decisiones de diseño](docs/es/design-decisions.md) para
  entender por qué las cosas están construidas así.

## Entorno de desarrollo

```bash
git clone https://github.com/<tu-cuenta>/Moneta.git
cd Moneta
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r ledger/requirements.txt pytest
python -m pytest -q ledger/tests              # funciona sin Internet (billetera, XMRig y cotizaciones simulados)
docker build -f ledger/Dockerfile .           # el contexto de build es la raíz del repositorio
```

Para trabajar en el ledger no necesitas ni un nodo de Monero ni un minero: las pruebas simulan ambos.

## Reglas básicas

**La privacidad primero: este es un repositorio público.**
- Nunca subas secretos: semilla, contraseñas, clave de visualización, tokens, `config.toml`, `.env`, bases de
  datos, archivos de billetera.
- Ningún dato personal del entorno: direcciones IP reales, nombres de usuario, direcciones de minería, nombres de
  host, tus propios servidores o proveedores de hosting. Usa marcadores como `<IP-NAS>`, `<USUARIO-NAS>`, `4...`.
- Revisa `git status` y `git diff --cached` antes de cada commit.

**Código (`ledger/`)**
- Python 3.12, solo biblioteca estándar + `openpyxl` (+ `tzdata`). Las nuevas dependencias necesitan una buena
  razón y una entrada en [`THIRD_PARTY.md`](THIRD_PARTY.md).
- Los nuevos archivos fuente empiezan con `# SPDX-License-Identifier: EUPL-1.2`.
- **Los datos fiscales son inmutables:** las cotizaciones, vatios, tarifas y costes guardados nunca se recalculan
  a posteriori. Los cambios de configuración solo se aplican hacia el futuro.
- **Migraciones de base de datos solo aditivas:** añadir las nuevas entradas al final de `db.MIGRATIONS`, nunca
  modificar las existentes.
- Importes en piconero (`int`), dinero como `Decimal`; redondear los EUR al céntimo por entrada y después sumar.
- Las consultas externas no deben permitir deducir el momento de pagos individuales.
- Endpoints POST solo con comprobación same-origin; el panel está pensado solo para la LAN.
- `python -m pytest -q ledger/tests` debe pasar; las nuevas funciones llevan pruebas (servicios simulados, sin
  Internet).
- Comentarios en inglés o alemán. La interfaz está por ahora en alemán; sus textos pasarán a archivos de
  traducción (ver hoja de ruta), así que mantén los nuevos textos breves y fáciles de extraer.

## Documentación y traducciones

- La documentación está en `docs/<de|en|fr|es>/` con **nombres de archivo idénticos**; cada página empieza con un
  selector de idioma.
- El alemán es la versión de referencia. Si cambias una página, actualiza los demás idiomas si puedes; si no,
  indícalo en el pull request y los sincronizaremos (o abre un issue "Translation").
- Las páginas fiscales describen el derecho alemán. Cita las normas con exactitud (§ 22 n.º 3 EStG, § 23 EStG,
  circular del BMF de 6 de marzo de 2025); describe lo que calcula la herramienta, sin dar asesoramiento fiscal.
- Cifras actuales (cotizaciones, hashrate, dificultad, precios de la electricidad) siempre con fecha y fuente.
- Un idioma nuevo es muy bienvenido: crea `docs/<código>/` con los mismos nombres de archivo y añádelo a
  [`docs/README.md`](docs/README.md) y a los selectores de idioma.

## Pull requests

1. Haz un fork del repositorio y crea una rama (`fix/…`, `feat/…`, `docs/…`).
2. Mantén los pull requests pequeños y enfocados; describe *qué* y *por qué*.
3. Para cambios visibles, añade una entrada en "Unreleased" de [`CHANGELOG.md`](CHANGELOG.md).
4. Las pruebas deben pasar y la lista de comprobación de la plantilla de pull request debe estar completa.

Las revisiones se hacen en tiempo libre; ten paciencia unos días. Las versiones las publican los mantenedores
(etiqueta `ledger-vX.Y.Z`, ver [operación](docs/es/operations.md)).

## Contribuciones asistidas por IA

Las contribuciones hechas con ayuda de herramientas de IA son bienvenidas. El repositorio contiene un
[`CLAUDE.md`](CLAUDE.md) con las reglas del proyecto para asistentes de programación. La responsabilidad sigue
siendo tuya: revísala, pruébala y asegúrate de que no contiene secretos ni datos personales.

## Seguridad

Por favor, **no** informes de vulnerabilidades en issues públicos; consulta [SECURITY.md](SECURITY.md).

## Licencia

Moneta tiene licencia [EUPL-1.2](LICENSE). Al enviar una contribución, aceptas que también se licencie bajo la
EUPL-1.2.
