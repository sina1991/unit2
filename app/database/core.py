from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    candle_time INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    tick_volume INTEGER,
    spread INTEGER,
    real_volume INTEGER,
    source_updated_at TEXT,
    UNIQUE (symbol, interval, candle_time)
);

CREATE INDEX IF NOT EXISTS idx_candles_series_time
    ON candles (symbol, interval, candle_time);

CREATE TABLE IF NOT EXISTS indicators (
    indicator_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    implementation_id TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    implementation_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'registered'
        CHECK (status IN ('registered', 'disabled', 'error')),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS indicator_parameter_sets (
    parameter_set_id TEXT PRIMARY KEY,
    indicator_id TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    parameters_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (indicator_id) REFERENCES indicators(indicator_id)
        ON DELETE RESTRICT,
    UNIQUE (indicator_id, parameters_hash)
);

CREATE TABLE IF NOT EXISTS indicator_values (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    candle_time INTEGER NOT NULL,
    indicator_id TEXT NOT NULL,
    parameter_set_id TEXT NOT NULL,
    output_name TEXT NOT NULL DEFAULT 'value',
    value REAL,
    status TEXT NOT NULL DEFAULT 'valid'
        CHECK (status IN ('valid', 'invalid', 'error', 'warmup')),
    calculation_version TEXT NOT NULL,
    calculated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (symbol, interval, candle_time)
        REFERENCES candles(symbol, interval, candle_time)
        ON DELETE CASCADE,
    FOREIGN KEY (indicator_id) REFERENCES indicators(indicator_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (parameter_set_id)
        REFERENCES indicator_parameter_sets(parameter_set_id)
        ON DELETE RESTRICT,
    UNIQUE (
        symbol, interval, candle_time, indicator_id,
        parameter_set_id, output_name, calculation_version
    )
);

CREATE INDEX IF NOT EXISTS idx_indicator_values_lookup
    ON indicator_values (
        symbol, interval, indicator_id, parameter_set_id, candle_time
    );

CREATE TABLE IF NOT EXISTS calculation_runs (
    run_id TEXT PRIMARY KEY,
    indicator_id TEXT,
    parameter_set_id TEXT,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    requested_start_time INTEGER,
    requested_end_time INTEGER,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    status TEXT NOT NULL
        CHECK (status IN ('pending', 'running', 'succeeded', 'partial', 'failed')),
    processed_count INTEGER NOT NULL DEFAULT 0,
    error_details TEXT,
    FOREIGN KEY (indicator_id) REFERENCES indicators(indicator_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (parameter_set_id)
        REFERENCES indicator_parameter_sets(parameter_set_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS indicator_instances (
    instance_id TEXT PRIMARY KEY,
    indicator_id TEXT NOT NULL,
    parameter_set_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'disabled', 'error')),
    historical_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (historical_status IN (
            'pending', 'running', 'completed', 'partial', 'failed'
        )),
    historical_checkpoint_time INTEGER,
    online_checkpoint_time INTEGER,
    config_path TEXT NOT NULL,
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (indicator_id) REFERENCES indicators(indicator_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (parameter_set_id)
        REFERENCES indicator_parameter_sets(parameter_set_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_indicator_instances_status
    ON indicator_instances(status, historical_status);

CREATE TABLE IF NOT EXISTS sync_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    status TEXT NOT NULL
        CHECK (status IN ('running', 'succeeded', 'partial', 'failed')),
    requested_start_time INTEGER,
    requested_end_time INTEGER,
    fetched_count INTEGER NOT NULL DEFAULT 0,
    inserted_or_updated_count INTEGER NOT NULL DEFAULT 0,
    error_details TEXT
);
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def initialize(database_path: str | Path) -> None:
    """Create the initial schema safely; repeated calls preserve existing data."""
    with connect(database_path) as connection:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {version} is newer than supported "
                f"version {SCHEMA_VERSION}"
            )

        connection.executescript(SCHEMA)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def connect_configured() -> sqlite3.Connection:
    """Open the configured analytics database."""
    from app.config import get_database_path

    return connect(get_database_path())


def initialize_configured() -> None:
    """Initialize the configured analytics database."""
    from app.config import get_database_path

    initialize(get_database_path())
