"""Simple moving average indicator."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.indicators.base import CandleInput, Indicator, IndicatorMetadata, IndicatorOutput


class MovingAverage(Indicator):
    """Calculate a simple moving average from candle closing prices."""

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            identifier="moving_average",
            display_name="Moving Average",
            implementation_version="1",
            description="Simple moving average calculated from candle close prices.",
            default_parameters={"period": 20},
            required_lookback=20,
        )

    def calculate(
        self,
        candles: Sequence[CandleInput],
        parameters: Mapping[str, Any],
    ) -> Sequence[IndicatorOutput]:
        resolved = self.validate_parameters(parameters)
        period = resolved["period"]

        if isinstance(period, bool) or not isinstance(period, int) or period < 1:
            raise ValueError("period must be a positive integer")

        closes: list[float] = []
        outputs: list[IndicatorOutput] = []

        for candle in candles:
            closes.append(float(candle.close))
            window = closes[-period:]

            if len(window) < period:
                value = None
            else:
                value = sum(window) / period

            outputs.append(
                IndicatorOutput(
                    time=candle.time,
                    values={f"ma_{period}": value},
                )
            )

        return outputs


MA = MovingAverage
