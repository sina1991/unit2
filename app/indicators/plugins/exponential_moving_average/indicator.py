"""Exponential Moving Average indicator plugin."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.indicators.base import (
    CandleInput,
    Indicator,
    IndicatorMetadata,
    IndicatorOutput,
)


class ExponentialMovingAverage(Indicator):

    @property
    def metadata(self):
        return IndicatorMetadata(
            identifier="exponential_moving_average",
            display_name="Exponential Moving Average",
            implementation_version="1",
            description="EMA calculated from candle close prices.",
            default_parameters={"period": 20},
            required_lookback=20,
        )

    def calculate(
        self,
        candles: Sequence[CandleInput],
        parameters: Mapping[str, Any],
    ):

        period = self.validate_parameters(parameters)["period"]

        alpha = 2 / (period + 1)

        ema = None
        outputs = []

        for candle in candles:
            close = float(candle.close)

            if ema is None:
                ema = close
            else:
                ema = (close - ema) * alpha + ema

            outputs.append(
                IndicatorOutput(
                    time=candle.time,
                    values={
                        f"ema_{period}": ema
                    },
                )
            )

        return outputs


EMA = ExponentialMovingAverage
