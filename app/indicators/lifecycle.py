"""Catalog discovery and persistent lifecycle management for indicators."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, get_settings
from app.database.core import connect_configured, initialize_configured
from app.indicators.base import Indicator
from app.indicators.candle_loader import CandleLoader
from app.indicators.engine import IndicatorEngine
from app.indicators.registry import register_indicator
from app.indicators.results import save_indicator_outputs


_INFRASTRUCTURE = {
    "__init__.py", "base.py", "registry.py", "results.py",
    "engine.py", "candle_loader.py", "service.py", "lifecycle.py",
}


def discover_indicators() -> list[dict[str, Any]]:
    """Discover concrete indicator classes in configured Python files."""
    roots = [
        (PROJECT_ROOT / item.strip()).resolve()
        for item in get_settings().indicator_paths.split(",")
        if item.strip()
    ]
    found: dict[str, dict[str, Any]] = {}

    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if path.name in _INFRASTRUCTURE:
                continue
            if any(part in {"active", "__pycache__"} for part in path.parts):
                continue

            module_name = f"_indicator_plugin_{path.stem}_{uuid.uuid4().hex}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)

            try:
                spec.loader.exec_module(module)
            except Exception:
                continue

            for candidate in vars(module).values():
                if (
                    not isinstance(candidate, type)
                    or candidate is Indicator
                    or not issubclass(candidate, Indicator)
                    or getattr(candidate, "__abstractmethods__", False)
                ):
                    continue
                try:
                    metadata = candidate().metadata
                    found[metadata.identifier] = {
                        "identifier": metadata.identifier,
                        "display_name": metadata.display_name,
                        "implementation_version": metadata.implementation_version,
                        "description": metadata.description,
                        "default_parameters": dict(metadata.default_parameters),
                        "required_lookback": metadata.required_lookback,
                        "source": str(path.relative_to(PROJECT_ROOT)),
                    }
                except Exception:
                    continue

    return sorted(found.values(), key=lambda item: item["identifier"])


def _load_indicator(identifier: str) -> Indicator:
    for item in discover_indicators():
        if item["identifier"] != identifier:
            continue
        source = (PROJECT_ROOT / item["source"]).resolve()
        spec = importlib.util.spec_from_file_location(
            f"_indicator_runtime_{uuid.uuid4().hex}", source
        )
        if spec is None or spec.loader is None:
            break
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for candidate in vars(module).values():
            if (
                isinstance(candidate, type)
                and candidate is not Indicator
                and issubclass(candidate, Indicator)
                and not getattr(candidate, "__abstractmethods__", False)
            ):
                instance = candidate()
                if instance.metadata.identifier == identifier:
                    return instance

    raise ValueError(f"Indicator not found: {identifier}")


def list_instances(
    *, connection: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    owns = connection is None
    conn = connection if connection is not None else connect_configured()
    try:
        rows = conn.execute("""
            SELECT i.*, p.parameters_json
            FROM indicator_instances i
            JOIN indicator_parameter_sets p
              ON p.parameter_set_id = i.parameter_set_id
            ORDER BY i.created_at, i.instance_id
        """).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["parameters"] = json.loads(item.pop("parameters_json"))
            result.append(item)
        return result
    finally:
        if owns:
            conn.close()


def activate_indicator(
    identifier: str,
    *,
    instance_id: str | None = None,
    parameters: dict[str, Any] | None = None,
    symbol: str = "XAUUSD",
    interval: str = "1m",
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Register an indicator instance and persist its configuration."""
    if not symbol or not interval:
        raise ValueError("symbol and interval are required")

    initialize_configured()
    indicator = _load_indicator(identifier)
    resolved = indicator.validate_parameters(parameters or {})

    if instance_id is None:
        suffix = "_".join(
            f"{key}{value}" for key, value in sorted(resolved.items())
        )
        instance_id = re.sub(
            r"[^A-Za-z0-9_-]+", "_", f"{identifier}_{suffix}".strip("_")
        )
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", instance_id):
        raise ValueError("Invalid instance_id")

    active_root = (PROJECT_ROOT / "app/indicators/active").resolve()
    instance_dir = active_root / instance_id
    config_path = instance_dir / "config.json"

    owns = connection is None
    conn = connection if connection is not None else connect_configured()
    created_dir = False

    try:
        existing = conn.execute(
            "SELECT 1 FROM indicator_instances WHERE instance_id = ?",
            (instance_id,),
        ).fetchone()
        if existing:
            raise ValueError(f"Instance already exists: {instance_id}")

        registered = register_indicator(
            indicator, resolved, connection=conn
        )
        instance_dir.mkdir(parents=True, exist_ok=False)
        created_dir = True

        config = {
            "instance_id": instance_id,
            "indicator_id": identifier,
            "parameter_set_id": registered["parameter_set_id"],
            "parameters": resolved,
            "symbol": symbol,
            "interval": interval,
        }
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        conn.execute("""
            INSERT INTO indicator_instances (
                instance_id, indicator_id, parameter_set_id,
                symbol, interval, config_path
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            instance_id, identifier, registered["parameter_set_id"],
            symbol, interval, str(config_path),
        ))
        if owns:
            conn.commit()
        return {**config, "status": "active", "historical_status": "pending"}
    except Exception:
        if owns:
            conn.rollback()
        if created_dir:
            shutil.rmtree(instance_dir, ignore_errors=True)
        raise
    finally:
        if owns:
            conn.close()


def set_instance_status(
    instance_id: str,
    status: str,
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    if status not in {"active", "disabled"}:
        raise ValueError("status must be active or disabled")
    owns = connection is None
    conn = connection if connection is not None else connect_configured()
    try:
        cursor = conn.execute("""
            UPDATE indicator_instances
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE instance_id = ?
        """, (status, instance_id))
        if cursor.rowcount == 0:
            raise ValueError(f"Instance not found: {instance_id}")
        if owns:
            conn.commit()
        return {"instance_id": instance_id, "status": status}
    except Exception:
        if owns:
            conn.rollback()
        raise
    finally:
        if owns:
            conn.close()


def delete_instance(
    instance_id: str,
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Delete an instance and its results without deleting shared definitions."""
    owns = connection is None
    conn = connection if connection is not None else connect_configured()
    config_path: Path | None = None
    try:
        row = conn.execute(
            "SELECT * FROM indicator_instances WHERE instance_id = ?",
            (instance_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Instance not found: {instance_id}")

        config_path = Path(row["config_path"]).resolve()
        conn.execute("""
            DELETE FROM indicator_values
            WHERE indicator_id = ? AND parameter_set_id = ?
              AND symbol = ? AND interval = ?
        """, (
            row["indicator_id"], row["parameter_set_id"],
            row["symbol"], row["interval"],
        ))
        conn.execute("""
            DELETE FROM calculation_runs
            WHERE indicator_id = ? AND parameter_set_id = ?
              AND symbol = ? AND interval = ?
        """, (
            row["indicator_id"], row["parameter_set_id"],
            row["symbol"], row["interval"],
        ))
        conn.execute(
            "DELETE FROM indicator_instances WHERE instance_id = ?",
            (instance_id,),
        )
        if owns:
            conn.commit()

        active_root = (PROJECT_ROOT / "app/indicators/active").resolve()
        if config_path.is_relative_to(active_root):
            shutil.rmtree(config_path.parent, ignore_errors=True)
        return {"instance_id": instance_id, "deleted": True}
    except Exception:
        if owns:
            conn.rollback()
        raise
    finally:
        if owns:
            conn.close()


def run_instance_batch(
    instance_id: str,
    *,
    mode: str = "historical",
    batch_size: int = 500,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Run one resumable historical or incremental calculation batch."""
    if mode not in {"historical", "online"}:
        raise ValueError("mode must be historical or online")
    if not 1 <= batch_size <= 10000:
        raise ValueError("batch_size must be between 1 and 10000")

    initialize_configured()
    owns = connection is None
    conn = connection if connection is not None else connect_configured()
    try:
        row = conn.execute("""
            SELECT i.*, p.parameters_json
            FROM indicator_instances i
            JOIN indicator_parameter_sets p
              ON p.parameter_set_id = i.parameter_set_id
            WHERE i.instance_id = ?
        """, (instance_id,)).fetchone()
        if row is None:
            raise ValueError(f"Instance not found: {instance_id}")
        if row["status"] != "active":
            raise ValueError(f"Instance is not active: {instance_id}")

        checkpoint_col = (
            "historical_checkpoint_time"
            if mode == "historical" else "online_checkpoint_time"
        )
        checkpoint = row[checkpoint_col]
        indicator = _load_indicator(row["indicator_id"])
        parameters = json.loads(row["parameters_json"])
        period = parameters.get("period", indicator.metadata.required_lookback)
        lookback = max(
            1, int(period) if isinstance(period, (int, float)) else 1
        )

        loader = CandleLoader(connection=conn)
        if checkpoint is None:
            batch = loader.load(
                row["symbol"], row["interval"], limit=batch_size
            )
        else:
            batch = loader.load_after(
                row["symbol"], row["interval"], checkpoint, limit=batch_size
            )

        if not batch:
            if mode == "historical":
                conn.execute("""
                    UPDATE indicator_instances
                    SET historical_status = 'completed',
                        online_checkpoint_time = COALESCE(
                            online_checkpoint_time, historical_checkpoint_time
                        ),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE instance_id = ?
                """, (instance_id,))
            if owns:
                conn.commit()
            return {
                "instance_id": instance_id,
                "mode": mode,
                "processed_count": 0,
                "checkpoint_time": checkpoint,
                "completed": True,
            }

        first_time = batch[0]["candle_time"]
        context = conn.execute("""
            SELECT symbol, interval, candle_time, open, high, low, close,
                   tick_volume, spread, real_volume, source_updated_at
            FROM candles
            WHERE symbol = ? AND interval = ? AND candle_time < ?
            ORDER BY candle_time DESC LIMIT ?
        """, (
            row["symbol"], row["interval"], first_time, lookback - 1
        )).fetchall()
        candles = [dict(item) for item in reversed(context)] + batch
        outputs = IndicatorEngine().calculate(
            indicator, candles, parameters=parameters
        )
        batch_times = {item["candle_time"] for item in batch}
        outputs = [item for item in outputs if item.time in batch_times]

        save_indicator_outputs(
            outputs,
            symbol=row["symbol"],
            interval=row["interval"],
            indicator_id=row["indicator_id"],
            parameter_set_id=row["parameter_set_id"],
            calculation_version=indicator.metadata.implementation_version,
            connection=conn,
        )

        new_checkpoint = batch[-1]["candle_time"]
        conn.execute(f"""
            UPDATE indicator_instances
            SET {checkpoint_col} = ?,
                historical_status = CASE
                    WHEN ? = 'historical' THEN 'running'
                    ELSE historical_status
                END,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE instance_id = ?
        """, (new_checkpoint, mode, instance_id))
        if owns:
            conn.commit()
        return {
            "instance_id": instance_id,
            "mode": mode,
            "processed_count": len(batch),
            "saved_value_count": sum(len(item.values) for item in outputs),
            "checkpoint_time": new_checkpoint,
            "completed": len(batch) < batch_size,
        }
    except Exception as exc:
        if owns:
            conn.rollback()
        try:
            conn.execute("""
                UPDATE indicator_instances
                SET last_error = ?, updated_at = CURRENT_TIMESTAMP
                WHERE instance_id = ?
            """, (str(exc), instance_id))
            if owns:
                conn.commit()
        except sqlite3.Error:
            pass
        raise
    finally:
        if owns:
            conn.close()
