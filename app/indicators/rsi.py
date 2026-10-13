"""Relative Strength Index (RSI) using Wilder's smoothing."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.indicators.base import (
    CandleInput,
    Indicator,
    IndicatorMetadata,
    IndicatorOutput,
)


class RelativeStrengthIndex(Indicator):
    """Calculate RSI from candle closing prices."""

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            identifier="relative_strength_index",
            display_name="Relative Strength Index (RSI)",
            implementation_version="1",
            description="RSI calculated from candle close prices using Wilder's smoothing.",
            default_parameters={"period": 14},
            required_lookback=15,
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

        outputs: list[IndicatorOutput] = []
        previous_close: float | None = None
        gains: list[float] = []
        losses: list[float] = []
        average_gain: float | None = None
        average_loss: float | None = None

        for candle in candles:
            close = float(candle.close)
            value: float | None = None

            if previous_close is not None:
                change = close - previous_close
                gain = max(change, 0.0)
                loss = max(-change, 0.0)

                if average_gain is None or average_loss is None:
                    gains.append(gain)
                    losses.append(loss)

                    if len(gains) == period:
                        average_gain = sum(gains) / period
                        average_loss = sum(losses) / period
                else:
                    average_gain = (
                        average_gain * (period - 1) + gain
                    ) / period
                    average_loss = (
                        average_loss * (period - 1) + loss
                    ) / period

                if average_gain is not None and average_loss is not None:
                    if average_gain == 0 and average_loss == 0:
                        value = 50.0
                    elif average_loss == 0:
                        value = 100.0
                    elif average_gain == 0:
                        value = 0.0
                    else:
                        relative_strength = average_gain / average_loss
                        value = 100.0 - (
                            100.0 / (1.0 + relative_strength)
                        )

            outputs.append(
                IndicatorOutput(
                    time=candle.time,
                    values={f"rsi_{period}": value},
                )
            )
            previous_close = close

        return outputs


RSI = RelativeStrengthIndex
