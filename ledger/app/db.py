# SPDX-License-Identifier: EUPL-1.2
"""SQLite-Datenbank: Schema, Migrationen und Verbindungen (eine Verbindung pro Thread).

Regel für künftige Änderungen: Migrationen sind nur additiv (neue Tabellen/Spalten).
Bereits erfasste, steuerlich relevante Werte (Kurse, Watt, Tarife, Kosten) werden nie
nachträglich umgeschrieben.
"""
from __future__ import annotations

import sqlite3
import threading
import time

BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS inflows (
    txid         TEXT PRIMARY KEY,
    height       INTEGER NOT NULL,
    ts           INTEGER NOT NULL,          -- Blockzeit (Unix)
    amount       INTEGER NOT NULL,          -- Piconero (1 XMR = 1e12)
    kind         TEXT NOT NULL,             -- 'block' = Mining-Auszahlung (Coinbase), 'in' = sonstiger Zugang
    price_eur    TEXT,                      -- EUR je XMR zum Zuflusszeitpunkt (Dezimal als Text)
    price_ts     INTEGER,                   -- Zeitpunkt des verwendeten Kurses
    price_source TEXT,
    first_seen   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS disposals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           INTEGER NOT NULL,          -- Zeitpunkt des Abgangs
    amount       INTEGER NOT NULL,          -- Piconero inkl. Netzwerkgebühr
    kind         TEXT NOT NULL,             -- 'sale' (Verkauf/Tausch), 'spend' (Bezahlung), 'own' (Übertrag auf eigene Wallet)
    proceeds_eur TEXT,                      -- Erlös/Gegenwert in EUR (bei sale/spend)
    txid         TEXT,
    note         TEXT,
    created      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS power_daily (
    day            TEXT NOT NULL,           -- YYYY-MM-DD (lokale Zeit)
    device         TEXT NOT NULL,
    mining_seconds INTEGER NOT NULL DEFAULT 0,
    kwh            REAL NOT NULL DEFAULT 0,
    cost_eur       REAL NOT NULL DEFAULT 0,
    hr_sum         REAL NOT NULL DEFAULT 0,
    hr_n           INTEGER NOT NULL DEFAULT 0,
    watts_last     REAL,
    tariff_last    REAL,
    PRIMARY KEY (day, device)
);

CREATE TABLE IF NOT EXISTS power_samples (
    ts        INTEGER NOT NULL,
    device    TEXT NOT NULL,
    reachable INTEGER NOT NULL,
    mining    INTEGER NOT NULL,
    hashrate  REAL,
    seconds   INTEGER NOT NULL,
    watts     REAL NOT NULL,
    tariff_ct REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_samples_ts ON power_samples(ts);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

# Index = Zielversion. Nur anhängen, nie ändern.
MIGRATIONS: list[str] = [
    BASE_SCHEMA,  # 1: Ausgangsstand (v1.0.0)
    # 2: lokale Kurshistorie (5-Minuten-Werte), damit Kursabfragen nicht mehr
    #    den Zeitpunkt einzelner Auszahlungen verraten
    """
    CREATE TABLE IF NOT EXISTS price_points (
        ts     INTEGER PRIMARY KEY,   -- Unix-Zeit des Kurspunkts
        eur    TEXT NOT NULL,         -- EUR je XMR
        source TEXT NOT NULL
    );
    """,
    # 3: Auswertung über beliebige Zeiträume (nur Anzeige, keine Steuergrundlage):
    #    Stundenwerte je Gerät (Minutenwerte werden nach 30 Tagen gelöscht) und
    #    Difficulty/Blockbelohnung vom eigenen Node für den rechnerischen Gegenwert
    """
    CREATE TABLE IF NOT EXISTS activity_hourly (
        hour      INTEGER NOT NULL,   -- Unix-Zeit des Stundenbeginns
        device    TEXT NOT NULL,
        polls     INTEGER NOT NULL DEFAULT 0,
        mining_s  INTEGER NOT NULL DEFAULT 0,
        paused_s  INTEGER NOT NULL DEFAULT 0,   -- erreichbar, aber pausiert bzw. ohne Hashrate
        offline_s INTEGER NOT NULL DEFAULT 0,   -- XMRig-API nicht erreichbar
        hashes    REAL NOT NULL DEFAULT 0,      -- Hashrate x Intervall
        hr_max    REAL NOT NULL DEFAULT 0,
        kwh       REAL NOT NULL DEFAULT 0,
        cost_eur  REAL NOT NULL DEFAULT 0,
        PRIMARY KEY (hour, device)
    );
    CREATE TABLE IF NOT EXISTS network_samples (
        height     INTEGER PRIMARY KEY,
        ts         INTEGER NOT NULL,   -- Blockzeit
        difficulty INTEGER NOT NULL,
        reward     INTEGER NOT NULL    -- Blockbelohnung in Piconero (inkl. Gebühren)
    );
    CREATE INDEX IF NOT EXISTS idx_network_ts ON network_samples(ts);
    """,
]

_local = threading.local()
_path: str | None = None
write_lock = threading.Lock()


def init(path: str) -> int:
    """Öffnet die Datenbank und bringt das Schema auf den neuesten Stand. Gibt die Version zurück."""
    global _path
    _path = path
    conn = get()
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for target, sql in enumerate(MIGRATIONS, start=1):
        if version < target:
            with write_lock:
                conn.executescript(sql)
                conn.execute(f"PRAGMA user_version = {target}")
                conn.commit()
            version = target
    return version


def get() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def close_thread() -> None:
    """Verbindung des aktuellen Threads schließen (z. B. am Ende einer Web-Anfrage)."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def set_meta(key: str, value: str) -> None:
    with write_lock:
        c = get()
        c.execute("INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, value))
        c.commit()


def get_meta(key: str, default: str | None = None) -> str | None:
    row = get().execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def now() -> int:
    return int(time.time())
