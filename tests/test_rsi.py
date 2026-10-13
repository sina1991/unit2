import pytest

from app.indicators.base import CandleInput
from app.indicators.rsi import RelativeStrengthIndex


def make_candles(closes):
    return [
        CandleInput(
            time=i * 60,
            open=close,
            high=close,
            low=close,
            close=close,
        )
        for i, close in enumerate(closes)
    ]


def test_rsi_metadata_and_defaults():
    indicator = RelativeStrengthIndex()
    assert indicator.metadata.identifier == "relative_strength_index"
    assert indicator.validate_parameters({}) == {"period": 14}


def test_rsi_is_none_until_enough_price_changes():
    outputs = RelativeStrengthIndex().calculate(
        make_candles([10, 11, 12, 11]),
        {"period": 3},
    )
    values = [item.values["rsi_3"] for item in outputs]
    assert values[:3] == [None, None, None]
    assert values[3] == pytest.approx(66.6666666667)


def test_rsi_is_100_when_prices_only_rise():
    outputs = RelativeStrengthIndex().calculate(
        make_candles([10, 11, 12, 13]),
        {"period": 3},
    )
    assert outputs[-1].values["rsi_3"] == 100.0


def test_rsi_is_zero_when_prices_only_fall():
    outputs = RelativeStrengthIndex().calculate(
        make_candles([13, 12, 11, 10]),
        {"period": 3},
    )
    assert outputs[-1].values["rsi_3"] == 0.0


def test_rsi_is_50_when_prices_are_flat():
    outputs = RelativeStrengthIndex().calculate(
        make_candles([10, 10, 10, 10]),
        {"period": 3},
    )
    assert outputs[-1].values["rsi_3"] == 50.0


@pytest.mark.parametrize(
    ("period", "message"),
    [
        (0, "period must be a positive integer"),
        (-1, "period must be a positive integer"),
        (1.5, "period must be a positive integer"),
        (True, "Invalid parameter: period"),
    ],
)
def test_rsi_rejects_invalid_period(period, message):
    with pytest.raises(ValueError, match=message):
        RelativeStrengthIndex().calculate(
            make_candles([1, 2, 3]), {"period": period}
        )


def test_rsi_rejects_unknown_parameters():
    with pytest.raises(ValueError, match="Unsupported parameters"):
        RelativeStrengthIndex().calculate(make_candles([1, 2]), {"unknown": 3})


def test_rsi_preserves_all_candle_timestamps():
    candles = make_candles([10, 11, 10, 12, 11])
    outputs = RelativeStrengthIndex().calculate(candles, {"period": 2})
    assert [item.time for item in outputs] == [item.time for item in candles]
