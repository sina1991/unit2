from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from app.database.core import connect_configured, initialize_configured
from app.sync_service import sync_candles

@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(app.state, "disable_worker", False):
        yield
        return
    from app.worker import worker_loop

    stop_event = threading.Event()
    worker_thread = threading.Thread(
        target=worker_loop,
        args=(stop_event,),
        name="analytics-worker",
        daemon=True,
    )
    worker_thread.start()
    try:
        yield
    finally:
        stop_event.set()
        worker_thread.join(timeout=10)


app = FastAPI(
    lifespan=lifespan,
    title="db-analytics",
    version="0.1.0",
    description="Local analytics API for synchronized XAUUSD candles.",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "db-analytics"}


@app.get("/api/v1/candles")
def get_candles(
    limit: int = Query(default=100, ge=1, le=1000),
    start_time: int | None = Query(default=None, ge=0),
    end_time: int | None = Query(default=None, ge=0),
    symbol: str = "XAUUSD",
    interval: str = "1m",
) -> dict:
    if symbol != "XAUUSD" or interval != "1m":
        raise HTTPException(status_code=400, detail="Only XAUUSD/1m is supported")
    if start_time is not None and end_time is not None and start_time > end_time:
        raise HTTPException(status_code=400, detail="start_time must not exceed end_time")

    initialize_configured()
    clauses = ["symbol = ?", "interval = ?"]
    params: list = [symbol, interval]

    if start_time is not None:
        clauses.append("candle_time >= ?")
        params.append(start_time)
    if end_time is not None:
        clauses.append("candle_time <= ?")
        params.append(end_time)

    where = " AND ".join(clauses)
    with connect_configured() as connection:
        count = connection.execute(
            f"SELECT COUNT(*) FROM candles WHERE {where}", params
        ).fetchone()[0]
        rows = connection.execute(
            f"""SELECT candle_time, open, high, low, close,
                       tick_volume, spread, real_volume
                FROM candles WHERE {where}
                ORDER BY candle_time DESC LIMIT ?""",
            [*params, limit],
        ).fetchall()

    candles = [
        {
            "time": row["candle_time"],
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "tick_volume": row["tick_volume"],
            "spread": row["spread"],
            "real_volume": row["real_volume"],
        }
        for row in reversed(rows)
    ]
    return {
        "symbol": symbol,
        "interval": interval,
        "count": count,
        "returned": len(candles),
        "candles": candles,
    }


@app.get("/api/v1/candles/latest")
def get_latest_candle(
    symbol: str = "XAUUSD",
    interval: str = "1m",
) -> dict:
    if symbol != "XAUUSD" or interval != "1m":
        raise HTTPException(status_code=400, detail="Only XAUUSD/1m is supported")

    initialize_configured()
    with connect_configured() as connection:
        row = connection.execute(
            """SELECT candle_time, open, high, low, close,
                      tick_volume, spread, real_volume
               FROM candles
               WHERE symbol = ? AND interval = ?
               ORDER BY candle_time DESC LIMIT 1""",
            (symbol, interval),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="No candles available")

    candle = {
        "time": row["candle_time"],
        "open": row["open"],
        "high": row["high"],
        "low": row["low"],
        "close": row["close"],
        "tick_volume": row["tick_volume"],
        "spread": row["spread"],
        "real_volume": row["real_volume"],
    }
    return {"symbol": symbol, "interval": interval, "candle": candle}


@app.get("/api/v1/sync-runs")
def get_sync_runs(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    initialize_configured()
    with connect_configured() as connection:
        rows = connection.execute(
            """SELECT run_id, status, started_at, completed_at,
                      requested_start_time, requested_end_time,
                      fetched_count, inserted_or_updated_count, error_details
               FROM sync_runs ORDER BY started_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return {"runs": [dict(row) for row in rows], "returned": len(rows)}


@app.post("/api/v1/sync")
def run_sync(
    start_time: int | None = Query(default=None, ge=0),
    end_time: int | None = Query(default=None, ge=0),
    batch_size: int | None = Query(default=None, ge=1, le=1000),
) -> dict:
    try:
        return sync_candles(
            start_time=start_time,
            end_time=end_time,
            batch_size=batch_size,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# Indicator catalog and instance lifecycle API.
from pydantic import BaseModel, Field
from app.indicators.lifecycle import (
    activate_indicator,
    delete_instance,
    discover_indicators,
    list_instances,
    run_instance_batch,
    set_instance_status,
)
from app.indicators.results import query_indicator_values


class IndicatorActivationRequest(BaseModel):
    indicator_id: str
    instance_id: str | None = None
    parameters: dict = Field(default_factory=dict)
    symbol: str = "XAUUSD"
    interval: str = "1m"


class IndicatorStatusRequest(BaseModel):
    status: str


@app.get("/api/v1/indicators/catalog")
def get_indicator_catalog() -> dict:
    initialize_configured()
    try:
        discovered = discover_indicators()
        with connect_configured() as connection:
            rows = connection.execute(
                "SELECT indicator_id, status FROM indicators"
            ).fetchall()
        registered = {row["indicator_id"]: row["status"] for row in rows}

        for item in discovered:
            item["registered_status"] = registered.get(item["identifier"])

        return {"indicators": discovered, "returned": len(discovered)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/indicators/instances")
def get_indicator_instances() -> dict:
    initialize_configured()
    try:
        instances = list_instances()
        return {"instances": instances, "returned": len(instances)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/indicators/instances", status_code=201)
def post_indicator_instance(payload: IndicatorActivationRequest) -> dict:
    try:
        return activate_indicator(
            payload.indicator_id,
            instance_id=payload.instance_id,
            parameters=payload.parameters,
            symbol=payload.symbol,
            interval=payload.interval,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.patch("/api/v1/indicators/instances/{instance_id}")
def patch_indicator_instance(
    instance_id: str,
    payload: IndicatorStatusRequest,
) -> dict:
    try:
        return set_instance_status(instance_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/v1/indicators/instances/{instance_id}")
def remove_indicator_instance(instance_id: str) -> dict:
    try:
        return delete_instance(instance_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/indicators/instances/{instance_id}/run")
def run_indicator_instance(
    instance_id: str,
    mode: str = Query(default="historical", pattern="^(historical|online)$"),
    batch_size: int = Query(default=500, ge=1, le=10000),
) -> dict:
    try:
        return run_instance_batch(
            instance_id,
            mode=mode,
            batch_size=batch_size,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/indicators/instances/{instance_id}/values")
def get_indicator_instance_values(
    instance_id: str,
    start_time: int | None = Query(default=None, ge=0),
    end_time: int | None = Query(default=None, ge=0),
    output_name: str | None = None,
    limit: int = Query(default=1000, ge=1, le=10000),
) -> dict:
    if start_time is not None and end_time is not None and start_time > end_time:
        raise HTTPException(
            status_code=400,
            detail="start_time must not exceed end_time",
        )

    initialize_configured()
    with connect_configured() as connection:
        instance = connection.execute(
            """
            SELECT indicator_id, parameter_set_id, symbol, interval
            FROM indicator_instances
            WHERE instance_id = ?
            """,
            (instance_id,),
        ).fetchone()

        if instance is None:
            raise HTTPException(status_code=404, detail="Instance not found")

        values = query_indicator_values(
            symbol=instance["symbol"],
            interval=instance["interval"],
            indicator_id=instance["indicator_id"],
            parameter_set_id=instance["parameter_set_id"],
            start_time=start_time,
            end_time=end_time,
            output_name=output_name,
            limit=limit,
            connection=connection,
        )

    return {"instance_id": instance_id, "values": values, "returned": len(values)}
