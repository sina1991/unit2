"""ATR indicator plugin."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.indicators.base import (
    CandleInput,
    Indicator,
    IndicatorMetadata,
    IndicatorOutput,
)


class ATR(Indicator):

    @property
    def metadata(self):
        return IndicatorMetadata(
            identifier="atr",
            display_name="Average True Range",
            implementation_version="1",
            description="ATR volatility indicator.",
            default_parameters={"period": 14},
            required_lookback=14,
        )

    def calculate(
        self,
        candles: Sequence[CandleInput],
        parameters: Mapping[str, Any],
    ):

        period = self.validate_parameters(parameters)["period"]

        trs = []
        outputs = []

        previous_close = None

        for candle in candles:

            if previous_close is None:
                tr = candle.high - candle.low
            else:
                tr = max(
                    candle.high - candle.low,
                    abs(candle.high - previous_close),
                    abs(candle.low - previous_close),
                )

            trs.append(tr)
            previous_close = candle.close

            value = None

            if len(trs) >= period:
                value = sum(trs[-period:]) / period

            outputs.append(
                IndicatorOutput(
                    time=candle.time,
                    values={
                        f"atr_{period}": value
                    },
                )
            )

        return outputs
