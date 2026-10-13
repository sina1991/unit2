from __future__ import annotations

import sqlite3
from typing import Any

from app.database.core import connect_configured
from app.indicators.base import IndicatorOutput


def save_indicator_outputs(
    outputs: list[IndicatorOutput],
    *,
    symbol: str,
    interval: str,
    indicator_id: str,
    parameter_set_id: str,
    calculation_version: str,
    connection: sqlite3.Connection | None = None,
) -> int:
    """Insert or update indicator outputs; return the number of rows written."""
    if not symbol or not interval:
        raise ValueError("symbol and interval are required")
    if not indicator_id or not parameter_set_id or not calculation_version:
        raise ValueError(
            "indicator_id, parameter_set_id, and calculation_version are required"
        )

    rows: list[tuple[Any, ...]] = []

    for output in outputs:
        for output_name, value in output.values.items():
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
            ):
                raise ValueError(
                    f"Output {output_name!r} must be numeric or None"
                )

            rows.append(
                (
                    symbol,
                    interval,
                    output.time,
                    indicator_id,
                    parameter_set_id,
                    output_name,
                    value,
                    "valid" if value is not None else "warmup",
                    calculation_version,
                    None,
                )
            )

    owns_connection = connection is None
    conn = connection if connection is not None else connect_configured()

    try:
        conn.executemany(
            """
            INSERT INTO indicator_values (
                symbol,
                interval,
                candle_time,
                indicator_id,
                parameter_set_id,
                output_name,
                value,
                status,
                calculation_version,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (
                symbol,
                interval,
                candle_time,
                indicator_id,
                parameter_set_id,
                output_name,
                calculation_version
            ) DO UPDATE SET
                value = excluded.value,
                status = excluded.status,
                calculation_version = excluded.calculation_version,
                calculated_at = CURRENT_TIMESTAMP,
                error_message = excluded.error_message
            """,
            rows,
        )
        if owns_connection:
            conn.commit()
        return len(rows)
    except Exception:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        if owns_connection:
            conn.close()


def query_indicator_values(
    *,
    symbol: str,
    interval: str,
    indicator_id: str,
    parameter_set_id: str,
    start_time: int | None = None,
    end_time: int | None = None,
    output_name: str | None = None,
    limit: int = 1000,
    connection: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Return indicator values in ascending candle-time order."""
    if limit < 1 or limit > 10000:
        raise ValueError("limit must be between 1 and 10000")
    if start_time is not None and end_time is not None and start_time > end_time:
        raise ValueError("start_time must not be greater than end_time")

    clauses = [
        "symbol = ?",
        "interval = ?",
        "indicator_id = ?",
        "parameter_set_id = ?",
    ]
    params: list[Any] = [
        symbol,
        interval,
        indicator_id,
        parameter_set_id,
    ]

    if start_time is not None:
        clauses.append("candle_time >= ?")
        params.append(start_time)
    if end_time is not None:
        clauses.append("candle_time <= ?")
        params.append(end_time)
    if output_name is not None:
        clauses.append("output_name = ?")
        params.append(output_name)

    params.append(limit)

    owns_connection = connection is None
    conn = connection if connection is not None else connect_configured()

    try:
        rows = conn.execute(
            f"""
            SELECT
                symbol,
                interval,
                candle_time,
                indicator_id,
                parameter_set_id,
                output_name,
                value,
                status,
                calculation_version,
                calculated_at,
                error_message
            FROM indicator_values
            WHERE {' AND '.join(clauses)}
            ORDER BY candle_time ASC, output_name ASC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        if owns_connection:
            conn.close()
