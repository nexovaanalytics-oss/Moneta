# XMR-Ledger + monero-wallet-rpc (offizielle Monero-CLI, Prüfsumme gegen getmonero.org/hashes.txt)
# Lizenz: EUPL-1.2 (siehe LICENSE). Enthaltene Fremdsoftware: siehe THIRD_PARTY.md;
# die Monero-Lizenz (BSD-3-Clause) liegt im Image unter /usr/share/doc/monero/LICENSE.
# Build-Kontext ist das Repository-Wurzelverzeichnis:  docker build -f ledger/Dockerfile .
FROM python:3.12-slim

# Monero-Version: muss in https://www.getmonero.org/downloads/hashes.txt stehen.
# Bei einem Monero-Update hier anpassen (siehe docs/de/operations.md; EN: docs/en/operations.md).
ARG MONERO_VERSION=v0.18.5.4

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl bzip2 ca-certificates tzdata \
 && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    cd /tmp; \
    f="monero-linux-x64-${MONERO_VERSION}.tar.bz2"; \
    curl -fsSL -o hashes.txt https://www.getmonero.org/downloads/hashes.txt; \
    h="$(grep -F "$f" hashes.txt | grep -oE '[0-9a-f]{64}' | head -n1)"; \
    if [ -z "$h" ]; then echo "Monero ${MONERO_VERSION} nicht in hashes.txt – MONERO_VERSION anpassen"; exit 1; fi; \
    curl -fsSL -o "$f" "https://downloads.getmonero.org/cli/$f"; \
    echo "$h  $f" | sha256sum -c -; \
    tar -xjf "$f"; \
    cp monero-*/monero-wallet-rpc /usr/local/bin/; \
    mkdir -p /usr/share/doc/monero; \
    if [ -f monero-*/LICENSE ]; then cp monero-*/LICENSE /usr/share/doc/monero/LICENSE; \
    else curl -fsSL -o /usr/share/doc/monero/LICENSE "https://raw.githubusercontent.com/monero-project/monero/${MONERO_VERSION}/LICENSE"; fi; \
    rm -rf /tmp/*; \
    monero-wallet-rpc --version

COPY ledger/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

WORKDIR /app
COPY ledger/app/ /app/
COPY LICENSE THIRD_PARTY.md /usr/share/doc/xmr-ledger/

ARG APP_VERSION=dev
ARG GIT_SHA=
ENV APP_VERSION=${APP_VERSION} \
    GIT_SHA=${GIT_SHA} \
    TZ=Europe/Berlin \
    PYTHONUNBUFFERED=1

EXPOSE 8090
# Für den wallet-rpc-Container wird der Healthcheck in compose.yaml abgeschaltet.
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=4)" || exit 1
CMD ["python", "main.py", "--config", "/data/config.toml"]
