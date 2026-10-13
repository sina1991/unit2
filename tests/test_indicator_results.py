import sqlite3
import hashlib

import pytest

from app.database.core import initialize
from app.indicators.base import IndicatorOutput
from app.indicators.results import (
    query_indicator_values,
    save_indicator_outputs,
)


@pytest.fixture
def db_connection(tmp_path):
    path = tmp_path / "results.db"
    initialize(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        """
        INSERT INTO indicators (
            indicator_id, display_name, implementation_id,
            implementation_version
        ) VALUES (?, ?, ?, ?)
        """,
        ("test.example", "Test Example", "test.example", "1.0.0"),
    )

    parameters_json = "{}"
    conn.execute(
        """
        INSERT INTO indicator_parameter_sets (
            parameter_set_id, indicator_id, parameters_json, parameters_hash
        ) VALUES (?, ?, ?, ?)
        """,
        (
            "params-1",
            "test.example",
            parameters_json,
            hashlib.sha256(parameters_json.encode("utf-8")).hexdigest(),
        ),
    )

    for candle_time in (100, 160):
        conn.execute(
            """
            INSERT INTO candles (
                symbol, interval, candle_time, open, high, low, close
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("XAUUSD", "1m", candle_time, 1.0, 1.0, 1.0, 1.0),
        )

    conn.commit()
    try:
        yield conn
    finally:
        conn.close()


def test_save_and_query_indicator_outputs(db_connection):
    outputs = [
        IndicatorOutput(time=160, values={"value": 12.5}),
        IndicatorOutput(time=100, values={"value": 10.0}),
    ]

    written = save_indicator_outputs(
        outputs,
        symbol="XAUUSD",
        interval="1m",
        indicator_id="test.example",
        parameter_set_id="params-1",
        calculation_version="1.0.0",
        connection=db_connection,
    )

    assert written == 2

    rows = query_indicator_values(
        symbol="XAUUSD",
        interval="1m",
        indicator_id="test.example",
        parameter_set_id="params-1",
        connection=db_connection,
    )

    assert [row["candle_time"] for row in rows] == [100, 160]
    assert [row["value"] for row in rows] == [10.0, 12.5]
    assert all(row["status"] == "valid" for row in rows)


def test_saving_same_key_updates_existing_value(db_connection):
    args = {
        "symbol": "XAUUSD",
        "interval": "1m",
        "indicator_id": "test.example",
        "parameter_set_id": "params-1",
        "calculation_version": "1.0.0",
        "connection": db_connection,
    }

    save_indicator_outputs(
        [IndicatorOutput(time=100, values={"value": 10.0})],
        **args,
    )
    save_indicator_outputs(
        [IndicatorOutput(time=100, values={"value": 11.0})],
        **args,
    )

    rows = query_indicator_values(
        symbol="XAUUSD",
        interval="1m",
        indicator_id="test.example",
        parameter_set_id="params-1",
        connection=db_connection,
    )

    assert len(rows) == 1
    assert rows[0]["value"] == 11.0


def test_missing_output_is_saved_with_warmup_status(db_connection):
    save_indicator_outputs(
        [IndicatorOutput(time=100, values={"value": None})],
        symbol="XAUUSD",
        interval="1m",
        indicator_id="test.example",
        parameter_set_id="params-1",
        calculation_version="1.0.0",
        connection=db_connection,
    )

    rows = query_indicator_values(
        symbol="XAUUSD",
        interval="1m",
        indicator_id="test.example",
        parameter_set_id="params-1",
        connection=db_connection,
    )

    assert len(rows) == 1
    assert rows[0]["value"] is None
    assert rows[0]["status"] == "warmup"


def test_query_filters_time_range_and_output_name(db_connection):
    save_indicator_outputs(
        [
            IndicatorOutput(time=100, values={"fast": 1.0, "slow": 2.0}),
            IndicatorOutput(time=160, values={"fast": 3.0, "slow": 4.0}),
        ],
        symbol="XAUUSD",
        interval="1m",
        indicator_id="test.example",
        parameter_set_id="params-1",
        calculation_version="1.0.0",
        connection=db_connection,
    )

    rows = query_indicator_values(
        symbol="XAUUSD",
        interval="1m",
        indicator_id="test.example",
        parameter_set_id="params-1",
        start_time=100,
        end_time=100,
        output_name="slow",
        connection=db_connection,
    )

    assert len(rows) == 1
    assert rows[0]["candle_time"] == 100
    assert rows[0]["output_name"] == "slow"
    assert rows[0]["value"] == 2.0


def test_invalid_query_range_is_rejected():
    with pytest.raises(ValueError, match="start_time"):
        query_indicator_values(
            symbol="XAUUSD",
            interval="1m",
            indicator_id="test.example",
            parameter_set_id="params-1",
            start_time=200,
            end_time=100,
        )
