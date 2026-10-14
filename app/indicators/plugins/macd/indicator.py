"""MACD indicator plugin."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.indicators.base import (
    CandleInput,
    Indicator,
    IndicatorMetadata,
    IndicatorOutput,
)


class MACD(Indicator):

    @property
    def metadata(self):
        return IndicatorMetadata(
            identifier="macd",
            display_name="MACD",
            implementation_version="1",
            description="Moving Average Convergence Divergence.",
            default_parameters={
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
            },
            required_lookback=26,
        )

    def calculate(
        self,
        candles: Sequence[CandleInput],
        parameters: Mapping[str, Any],
    ):

        p = self.validate_parameters(parameters)

        fast = p["fast_period"]
        slow = p["slow_period"]
        signal_period = p["signal_period"]

        fast_ema = None
        slow_ema = None
        signal = None

        fast_alpha = 2 / (fast + 1)
        slow_alpha = 2 / (slow + 1)
        signal_alpha = 2 / (signal_period + 1)

        outputs = []

        for candle in candles:

            close = float(candle.close)

            fast_ema = (
                close
                if fast_ema is None
                else (close-fast_ema)*fast_alpha+fast_ema
            )

            slow_ema = (
                close
                if slow_ema is None
                else (close-slow_ema)*slow_alpha+slow_ema
            )

            macd_value = fast_ema - slow_ema

            signal = (
                macd_value
                if signal is None
                else (macd_value-signal)*signal_alpha+signal
            )

            outputs.append(
                IndicatorOutput(
                    time=candle.time,
                    values={
                        "macd": macd_value,
                        "macd_signal": signal,
                        "macd_histogram": macd_value-signal,
                    },
                )
            )

        return outputs
