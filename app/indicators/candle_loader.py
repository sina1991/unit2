"""Load historical candle data from the configured SQLite database."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.database.core import connect_configured


class CandleLoader:
    """Load candles in chronological order from the existing candles table."""

    def __init__(
        self,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        self.connection = connection

    def load(
        self,
        symbol: str,
        interval: str,
        *,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        if not symbol or not interval:
            raise ValueError("symbol and interval are required")
        if start_time is not None and end_time is not None:
            if start_time > end_time:
                raise ValueError("start_time must not exceed end_time")
        if limit is not None and limit < 1:
            raise ValueError("limit must be greater than zero")

        clauses = ["symbol = ?", "interval = ?"]
        params: list[Any] = [symbol, interval]

        if start_time is not None:
            clauses.append("candle_time >= ?")
            params.append(start_time)
        if end_time is not None:
            clauses.append("candle_time <= ?")
            params.append(end_time)

        sql = """
            SELECT
                symbol, interval, candle_time,
                open, high, low, close,
                tick_volume, spread, real_volume, source_updated_at
            FROM candles
            WHERE
        """ + " AND ".join(clauses) + " ORDER BY candle_time ASC"

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        owns_connection = self.connection is None
        conn = self.connection if self.connection is not None else connect_configured()

        try:
            return [
                dict(row)
                for row in conn.execute(sql, params).fetchall()
            ]
        finally:
            if owns_connection:
                conn.close()

    def load_after(
        self,
        symbol: str,
        interval: str,
        candle_time: int,
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Load candles strictly newer than the supplied checkpoint."""
        if not symbol or not interval:
            raise ValueError("symbol and interval are required")
        if limit is not None and limit < 1:
            raise ValueError("limit must be greater than zero")

        sql = """
            SELECT
                symbol, interval, candle_time,
                open, high, low, close,
                tick_volume, spread, real_volume, source_updated_at
            FROM candles
            WHERE symbol = ? AND interval = ? AND candle_time > ?
            ORDER BY candle_time ASC
        """
        params: list[Any] = [symbol, interval, candle_time]

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        owns_connection = self.connection is None
        conn = self.connection if self.connection is not None else connect_configured()

        try:
            return [
                dict(row)
                for row in conn.execute(sql, params).fetchall()
            ]
        finally:
            if owns_connection:
                conn.close()
