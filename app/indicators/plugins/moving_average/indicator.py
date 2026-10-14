"""Moving Average indicator plugin."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.indicators.base import (
    CandleInput,
    Indicator,
    IndicatorMetadata,
    IndicatorOutput,
)


class MovingAverage(Indicator):
    """Calculate simple moving average."""

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

        if isinstance(period, bool) or not isinstance(period, int):
            raise ValueError("period must be integer")

        if period < 1:
            raise ValueError("period must be positive")

        closes = []
        outputs = []

        for candle in candles:
            closes.append(float(candle.close))

            value = None
            if len(closes) >= period:
                value = sum(closes[-period:]) / period

            outputs.append(
                IndicatorOutput(
                    time=candle.time,
                    values={
                        f"ma_{period}": value
                    },
                )
            )

        return outputs


MA = MovingAverage
