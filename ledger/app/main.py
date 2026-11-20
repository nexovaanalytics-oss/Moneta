# SPDX-License-Identifier: EUPL-1.2
"""XMR-Ledger: Dokumentation für Monero-Mining (Zuflüsse, Kurse, Strom, § 23-Lose)."""
from __future__ import annotations

import argparse
import logging
import os
import signal
import threading

import activity
import config
import db
import miners
import network
import prices
import shares
import version
import walletsync
import web


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="/data/config.toml")
    args = ap.parse_args()

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = config.load(args.config)
    os.makedirs(cfg.data_dir, exist_ok=True)
    schema = db.init(os.path.join(cfg.data_dir, "ledger.sqlite"))
    logging.info("%s gestartet (DB-Schema v%d, %d Rechner)", version.label(), schema, len(miners.current(cfg)))
    for m in miners.current(cfg):
        if m.watts <= 0:
            logging.warning("%s: watts = 0 – für dieses Gerät werden keine Stromkosten erfasst", m.name)

    activity.backfill_hourly(cfg)  # einmalig nach Migration 3, bevor neue Abfragen gebucht werden

    stop = threading.Event()
    threads = [
        threading.Thread(target=walletsync.loop, args=(cfg, stop), name="wallet", daemon=True),
        threading.Thread(target=prices.loop, args=(cfg, stop), name="prices", daemon=True),
        threading.Thread(target=miners.loop, args=(cfg, stop), name="miners", daemon=True),
        threading.Thread(target=network.loop, args=(cfg, stop), name="network", daemon=True),
        threading.Thread(target=shares.loop, args=(cfg, stop), name="shares", daemon=True),
    ]
    for t in threads:
        t.start()

    srv = web.serve(cfg, stop)

    def shutdown(*_):
        logging.info("Beende …")
        stop.set()
        threading.Thread(target=srv.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    srv.serve_forever()


if __name__ == "__main__":
    main()
