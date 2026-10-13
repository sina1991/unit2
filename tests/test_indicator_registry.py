import sqlite3

import pytest

from app.database.core import initialize
from app.indicators.base import (
    CandleInput,
    Indicator,
    IndicatorMetadata,
    IndicatorOutput,
)
from app.indicators.registry import register_indicator


class ExampleIndicator(Indicator):
    @property
    def metadata(self):
        return IndicatorMetadata(
            identifier="test.example",
            display_name="Example Indicator",
            implementation_version="1.0.0",
            description="Registry test indicator.",
            default_parameters={"period": 5},
            required_lookback=0,
        )

    def calculate(self, candles, parameters):
        resolved = self.validate_parameters(parameters)
        return [
            IndicatorOutput(
                time=candle.time,
                values={"value": candle.close},
            )
            for candle in candles
        ]


@pytest.fixture
def db_connection(tmp_path):
    db_path = tmp_path / "registry-test.db"
    initialize(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def test_register_indicator_creates_indicator_and_parameter_set(db_connection):
    result = register_indicator(ExampleIndicator(), connection=db_connection)

    assert result["identifier"] == "test.example"
    assert result["parameters"] == {"period": 5}
    assert result["indicator_id"] == "test.example"
    assert isinstance(result["parameter_set_id"], str) and result["parameter_set_id"]

    indicator_count = db_connection.execute(
        "SELECT COUNT(*) FROM indicators WHERE indicator_id = ?",
        ("test.example",),
    ).fetchone()[0]
    parameter_count = db_connection.execute(
        """
        SELECT COUNT(*) FROM indicator_parameter_sets
        WHERE indicator_id = ?
        """,
        (result["indicator_id"],),
    ).fetchone()[0]

    assert indicator_count == 1
    assert parameter_count == 1


def test_registering_same_indicator_and_parameters_is_idempotent(
    db_connection,
):
    first = register_indicator(ExampleIndicator(), connection=db_connection)
    second = register_indicator(ExampleIndicator(), connection=db_connection)

    assert first["indicator_id"] == second["indicator_id"]
    assert first["parameter_set_id"] == second["parameter_set_id"]

    assert db_connection.execute(
        "SELECT COUNT(*) FROM indicators WHERE indicator_id = ?",
        ("test.example",),
    ).fetchone()[0] == 1

    assert db_connection.execute(
        "SELECT COUNT(*) FROM indicator_parameter_sets",
    ).fetchone()[0] == 1


def test_different_parameters_create_distinct_parameter_sets(db_connection):
    indicator = ExampleIndicator()

    first = register_indicator(indicator, connection=db_connection)
    second = register_indicator(
        indicator,
        {"period": 10},
        connection=db_connection,
    )

    assert first["parameter_set_id"] != second["parameter_set_id"]

    rows = db_connection.execute(
        """
        SELECT parameters_json
        FROM indicator_parameter_sets
        WHERE indicator_id = ?
        ORDER BY parameters_json
        """,
        (first["indicator_id"],),
    ).fetchall()

    assert len(rows) == 2
    assert {row["parameters_json"] for row in rows} == {
        '{"period":5}',
        '{"period":10}',
    }


def test_invalid_parameters_do_not_register_indicator(db_connection):
    with pytest.raises(ValueError):
        register_indicator(
            ExampleIndicator(),
            {"unknown": True},
            connection=db_connection,
        )

    count = db_connection.execute(
        "SELECT COUNT(*) FROM indicators",
    ).fetchone()[0]
    assert count == 0
