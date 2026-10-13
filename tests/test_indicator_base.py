import pytest

from app.indicators.base import (
    CandleInput,
    Indicator,
    IndicatorMetadata,
    IndicatorOutput,
)


class ExampleIndicator(Indicator):
    @property
    def metadata(self):
        return IndicatorMetadata(
            identifier="example.close",
            display_name="Close Value",
            implementation_version="1.0.0",
            description="Returns the candle close as an output.",
            default_parameters={"scale": 1},
            required_lookback=0,
        )

    def calculate(self, candles, parameters):
        resolved = self.validate_parameters(parameters)
        scale = resolved["scale"]
        return [
            IndicatorOutput(
                time=candle.time,
                values={"value": candle.close * scale},
            )
            for candle in candles
        ]


def test_metadata_has_stable_identifier_and_version():
    metadata = ExampleIndicator().metadata
    assert metadata.identifier == "example.close"
    assert metadata.implementation_version == "1.0.0"


def test_default_parameters_are_applied():
    indicator = ExampleIndicator()
    assert indicator.validate_parameters({}) == {"scale": 1}


def test_parameter_override_is_applied():
    indicator = ExampleIndicator()
    assert indicator.validate_parameters({"scale": 2}) == {"scale": 2}


def test_unknown_parameter_is_rejected():
    with pytest.raises(ValueError, match="Unsupported parameters"):
        ExampleIndicator().validate_parameters({"unknown": 5})


def test_invalid_parameter_type_is_rejected():
    with pytest.raises(ValueError, match="Invalid parameter"):
        ExampleIndicator().validate_parameters({"scale": []})


def test_calculation_preserves_candle_timestamps():
    indicator = ExampleIndicator()
    candles = [
        CandleInput(100, 10, 12, 9, 11),
        CandleInput(160, 11, 13, 10, 12),
    ]

    outputs = indicator.calculate(candles, {"scale": 2})

    assert [item.time for item in outputs] == [100, 160]
    assert [item.values["value"] for item in outputs] == [22, 24]


def test_output_supports_missing_values():
    output = IndicatorOutput(time=100, values={"value": None})
    assert output.values["value"] is None
