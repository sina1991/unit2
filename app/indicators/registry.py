from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from typing import Any

from app.database.core import connect_configured
from app.indicators.base import Indicator


def register_indicator(
    indicator: Indicator,
    parameters: dict[str, Any] | None = None,
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Register an indicator and parameter set idempotently."""
    metadata = indicator.metadata
    resolved_parameters = indicator.validate_parameters(parameters or {})

    parameters_json = json.dumps(
        resolved_parameters,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    parameters_hash = hashlib.sha256(
        parameters_json.encode("utf-8")
    ).hexdigest()

    owns_connection = connection is None
    conn = connection if connection is not None else connect_configured()

    try:
        if owns_connection:
            conn.execute("BEGIN IMMEDIATE")

        conn.execute(
            """
            INSERT INTO indicators (
                indicator_id,
                display_name,
                implementation_id,
                description,
                implementation_version,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(indicator_id) DO UPDATE SET
                display_name = excluded.display_name,
                implementation_id = excluded.implementation_id,
                description = excluded.description,
                implementation_version = excluded.implementation_version,
                metadata_json = excluded.metadata_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                metadata.identifier,
                metadata.display_name,
                metadata.identifier,
                metadata.description,
                metadata.implementation_version,
                json.dumps(
                    {
                        "default_parameters": metadata.default_parameters,
                        "required_lookback": metadata.required_lookback,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ),
            ),
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO indicator_parameter_sets (
                parameter_set_id,
                indicator_id,
                parameters_json,
                parameters_hash
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                metadata.identifier,
                parameters_json,
                parameters_hash,
            ),
        )

        parameter_row = conn.execute(
            """
            SELECT parameter_set_id
            FROM indicator_parameter_sets
            WHERE indicator_id = ? AND parameters_hash = ?
            """,
            (metadata.identifier, parameters_hash),
        ).fetchone()

        if parameter_row is None:
            raise RuntimeError("Parameter set registration failed.")

        if owns_connection:
            conn.commit()

        return {
            "indicator_id": metadata.identifier,
            "identifier": metadata.identifier,
            "parameter_set_id": parameter_row["parameter_set_id"],
            "parameters": resolved_parameters,
        }

    except Exception:
        if owns_connection:
            conn.rollback()
        raise

    finally:
        if owns_connection:
            conn.close()
