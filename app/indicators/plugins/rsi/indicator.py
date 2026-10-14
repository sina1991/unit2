"""RSI indicator plugin."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.indicators.base import (
    CandleInput,
    Indicator,
    IndicatorMetadata,
    IndicatorOutput,
)


class RSI(Indicator):

    @property
    def metadata(self):
        return IndicatorMetadata(
            identifier="rsi",
            display_name="Relative Strength Index",
            implementation_version="1",
            description="RSI momentum oscillator.",
            default_parameters={"period": 14},
            required_lookback=14,
        )

    def calculate(
        self,
        candles: Sequence[CandleInput],
        parameters: Mapping[str, Any],
    ):

        period = self.validate_parameters(parameters)["period"]

        closes = []
        outputs = []

        for candle in candles:
            closes.append(float(candle.close))

            value = None

            if len(closes) > period:
                gains = []
                losses = []

                for i in range(
                    len(closes)-period,
                    len(closes)
                ):
                    diff = closes[i] - closes[i-1]

                    if diff >= 0:
                        gains.append(diff)
                        losses.append(0)
                    else:
                        gains.append(0)
                        losses.append(abs(diff))

                avg_gain = sum(gains) / period
                avg_loss = sum(losses) / period

                if avg_loss == 0:
                    value = 100
                else:
                    rs = avg_gain / avg_loss
                    value = 100 - (100 / (1 + rs))

            outputs.append(
                IndicatorOutput(
                    time=candle.time,
                    values={
                        f"rsi_{period}": value
                    },
                )
            )

        return outputs
