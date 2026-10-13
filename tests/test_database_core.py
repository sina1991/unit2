import sqlite3

import pytest

from app.database.core import SCHEMA_VERSION, connect, initialize


def test_initialize_is_repeatable_and_preserves_data(tmp_path):
    database = tmp_path / "nested" / "analytics.db"

    initialize(database)
    with connect(database) as connection:
        connection.execute(
            """
            INSERT INTO candles (
                symbol, interval, candle_time, open, high, low, close
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("XAUUSD", "1m", 1000, 10.0, 12.0, 9.0, 11.0),
        )

    initialize(database)

    with connect(database) as connection:
        row = connection.execute(
            "SELECT symbol, interval, candle_time, close FROM candles"
        ).fetchone()
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert tuple(row) == ("XAUUSD", "1m", 1000, 11.0)
    assert version == SCHEMA_VERSION


def test_candle_series_timestamp_is_unique(tmp_path):
    database = tmp_path / "analytics.db"
    initialize(database)

    with connect(database) as connection:
        values = ("XAUUSD", "1m", 1000, 10.0, 12.0, 9.0, 11.0)
        connection.execute(
            """
            INSERT INTO candles (
                symbol, interval, candle_time, open, high, low, close
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO candles (
                    symbol, interval, candle_time, open, high, low, close
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )


def test_foreign_keys_are_enabled(tmp_path):
    database = tmp_path / "analytics.db"
    initialize(database)

    with connect(database) as connection:
        enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert enabled == 1
