# Operación

🌐 [Deutsch](../de/operations.md) · [English](../en/operations.md) · [Français](../fr/operations.md) · **Español**

Ejecuta todos los comandos del NAS por SSH en la carpeta del proyecto (ejemplo: `/volume1/docker/monero`),
siempre con el mismo nombre de proyecto (`-p monero-pool`; ajústalo al nombre de Container Manager si es
necesario).

## Chuleta

```bash
sudo docker ps --format "table {{.Names}}\t{{.Status}}"   # resumen
sudo docker logs --tail 5 monerod                          # progreso de sincronización
sudo docker exec monerod monerod status                    # altura, pares, hashrate
sudo docker attach p2pool                                  # luego "status"; salir con Ctrl+P, Ctrl+Q (¡no Ctrl+C!)
sudo docker logs --tail 30 xmr-ledger                      # ledger
sudo docker logs --tail 30 wallet-rpc                      # billetera de solo lectura
sudo docker restart xmr-ledger                             # tras cambiar config.toml
```

## Publicar una versión del ledger

En tu equipo, dentro del repositorio:

```bash
python -m pytest -q ledger/tests                 # debe pasar
# completar CHANGELOG.md, commit, push → imagen :edge
git tag ledger-v1.2.0 && git push origin ledger-v1.2.0   # → imagen :1.2.0
```

O en el navegador: GitHub → repositorio → **Releases → Draft a new release** → crear la nueva etiqueta
`ledger-v1.2.0` (destino: `main`) → título p. ej. "Ledger 1.2.0", texto de `CHANGELOG.md` → **Publish release**.

Después, esperar a GitHub → Actions → workflow "ledger" (pruebas + imagen).

## Acceso a la imagen

La imagen `ghcr.io/nexovaanalytics-oss/xmr-ledger` es pública; no hace falta `docker login`.
Para la imagen de un fork privado: `sudo docker login ghcr.io -u <usuario-github>` con un token (classic) con
`read:packages`.

## Desplegar una nueva versión del ledger en el NAS

**Con el script de actualización** (recomendado): pregunta a GitHub por la última versión `ledger-vX.Y.Z`,
muestra el cambio y pide confirmación. Después descarga la imagen (antes no se cambia nada), hace una copia de la base
de datos dentro del contenedor en marcha (`ledger/data/ledger-vor-X.Y.Z-<hora>.sqlite`, copia SQLite con WAL
incluido), fija `LEDGER_VERSION` en `.env`, reinicia `wallet-rpc` y `ledger`, y muestra el registro y cómo volver
atrás. La versión sigue fijada: el script solo se ejecuta cuando tú lo lanzas. Descárgalo una vez (léelo antes):

```bash
cd /volume1/docker/monero
sudo curl -fsSLo update-ledger.sh https://raw.githubusercontent.com/nexovaanalytics-oss/Moneta/main/deploy/nas/update-ledger.sh
cat update-ledger.sh
```

Luego, en cada actualización:

```bash
cd /volume1/docker/monero
sudo bash update-ledger.sh --check     # solo mostrar: versión fijada vs. última versión
sudo bash update-ledger.sh             # última versión, con confirmación
sudo bash update-ledger.sh 1.2.0       # una versión concreta
```

La única petición externa va a `api.github.com` (lista de releases), en el momento que elijas y sin relación con los
pagos.

**A mano:**

```bash
cd /volume1/docker/monero
sudo sed -i 's/^LEDGER_VERSION=.*/LEDGER_VERSION=1.2.0/' .env
sudo docker compose -p monero-pool pull wallet-rpc ledger
sudo docker compose -p monero-pool up -d wallet-rpc ledger
sudo docker logs --tail 10 xmr-ledger            # la línea de arranque muestra la versión y el esquema de BD
```

Volver atrás: restablecer `LEDGER_VERSION` y ejecutar `up -d` de nuevo. Atención: las migraciones de la base de
datos solo van hacia delante; haz una copia de `ledger/data/` antes de actualizaciones importantes.

## Actualizaciones de Monero y P2Pool

- **monerod/p2pool:** `sudo docker compose -p monero-pool pull monerod p2pool && sudo docker compose -p monero-pool up -d`.
  Obligatorio antes de los hard forks (anuncios en getmonero.org y en el repositorio de P2Pool).
- **wallet-rpc en la imagen del ledger:** subir `ARG MONERO_VERSION` en `ledger/Dockerfile` y publicar una nueva
  versión del ledger. El build falla si la versión no figura en getmonero.org/downloads/hashes.txt.

## Copias de seguridad

- Incluir `ledger/data/` (base de datos, `config.toml`, `kurse_manuell.csv`) y `.env` en la copia de seguridad
  (p. ej. Hyper Backup).
- `ledger/wallets/` no necesita copia (se puede recrear desde la clave de visualización).
- No copiar el volumen de la blockchain (se puede volver a sincronizar).
- Palabras de la semilla de la billetera de minería: solo en papel.

## Solución de problemas

| Síntoma | Causa / solución |
|---|---|
| Ledger: "Wallet-Sync fehlgeschlagen: … refused" | wallet-rpc aún está arrancando; volver a comprobar tras 2 min |
| Ledger: errores de sincronización de la billetera hasta que el nodo esté sincronizado | normal mientras monerod sincroniza |
| Equipo "nicht erreichbar" (inaccesible) | XMRig no se ejecuta con `--http-host 0.0.0.0`, equipo en reposo, cortafuegos de macOS, IP incorrecta |
| Registro: "XMRig-API lehnt das Token ab" (token rechazado) | token en `config.toml` ≠ archivo de token en el equipo |
| Equipo "pausiert" (en pausa) | XMRig accesible pero sin hashrate (pool inaccesible, con batería, en pausa); no cuesta nada |
| Entrada "Kurs fehlt" (falta cotización) | se completa en la siguiente consulta de cotizaciones; si no, `kurse_manuell.csv` |
| p2pool "unhealthy" | el nodo aún no está sincronizado, o el puerto ZMQ no coincide (18084) |
| Aviso de dos archivos Compose | conservar solo `compose.yaml` |
