from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.clients.db_gold import DbGoldClient
from app.database.core import connect_configured, initialize_configured

SYMBOL = "XAUUSD"
INTERVAL = "1m"


def sync_candles(
    start_time: int | None = None,
    end_time: int | None = None,
    batch_size: int | None = None,
) -> dict:
    """Synchronize XAUUSD 1m candles, paging backwards and upserting locally."""
    from app.config import get_settings

    settings = get_settings()
    limit = settings.sync_batch_size if batch_size is None else batch_size

    if not 1 <= limit <= 1000:
        raise ValueError("batch_size must be between 1 and 1000")
    if start_time is not None and end_time is not None and start_time > end_time:
        raise ValueError("start_time must not exceed end_time")

    initialize_configured()

    # Default behavior: first run downloads available history; later runs
    # resume from the latest local candle, with a one-minute overlap.
    with connect_configured() as connection:
        latest = connection.execute(
            """
            SELECT MAX(candle_time) AS latest_time
            FROM candles
            WHERE symbol = ? AND interval = ?
            """,
            (SYMBOL, INTERVAL),
        ).fetchone()["latest_time"]

    effective_start = start_time
    if effective_start is None and latest is not None:
        effective_start = max(0, int(latest) - 60)

    run_id = str(uuid.uuid4())
    with connect_configured() as connection:
        connection.execute(
            """
            INSERT INTO sync_runs (
                run_id, status, requested_start_time, requested_end_time
            ) VALUES (?, 'running', ?, ?)
            """,
            (run_id, effective_start, end_time),
        )

    fetched_count = 0
    upserted_count = 0
    cursor_end = end_time

    try:
        with DbGoldClient(settings=settings) as client:
            while True:
                response = client.fetch_candles(
                    limit=limit,
                    start_time=effective_start,
                    end_time=cursor_end,
                    symbol=SYMBOL,
                    interval=INTERVAL,
                )
                candles = response.candles
                if not candles:
                    break

                fetched_count += len(candles)

                with connect_configured() as connection:
                    for candle in candles:
                        cursor = connection.execute(
                            """
                            INSERT INTO candles (
                                symbol, interval, candle_time, open, high, low,
                                close, tick_volume, spread, real_volume
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(symbol, interval, candle_time)
                            DO UPDATE SET
                                open = excluded.open,
                                high = excluded.high,
                                low = excluded.low,
                                close = excluded.close,
                                tick_volume = excluded.tick_volume,
                                spread = excluded.spread,
                                real_volume = excluded.real_volume
                            """,
                            (
                                SYMBOL, INTERVAL, candle.time, candle.open,
                                candle.high, candle.low, candle.close,
                                candle.tick_volume, candle.spread,
                                candle.real_volume,
                            ),
                        )
                        upserted_count += max(cursor.rowcount, 0)

                oldest_time = min(candle.time for candle in candles)
                if len(candles) < limit:
                    break

                next_end = oldest_time - 60
                if effective_start is not None and next_end < effective_start:
                    break
                if cursor_end is not None and next_end >= cursor_end:
                    raise RuntimeError("Pagination cursor did not move backwards")
                cursor_end = next_end

        status = "succeeded"
        error_details = None

    except Exception as exc:
        status = "partial" if upserted_count else "failed"
        error_details = str(exc)[:2000]

    with connect_configured() as connection:
        connection.execute(
            """
            UPDATE sync_runs
            SET completed_at = ?, status = ?, fetched_count = ?,
                inserted_or_updated_count = ?, error_details = ?
            WHERE run_id = ?
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                status,
                fetched_count,
                upserted_count,
                error_details,
                run_id,
            ),
        )

    result = {
        "run_id": run_id,
        "status": status,
        "fetched_count": fetched_count,
        "inserted_or_updated_count": upserted_count,
    }
    if error_details is not None:
        result["error_details"] = error_details
    if status != "succeeded":
        raise RuntimeError(f"Sync {status}: {error_details}")
    return result
