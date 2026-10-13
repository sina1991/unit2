"""Execution engine for indicator implementations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.indicators.base import CandleInput, Indicator, IndicatorOutput


class IndicatorEngine:
    """Convert database candles to the indicator contract and calculate."""

    @staticmethod
    def _to_candle(row: Any) -> CandleInput:
        def get(name: str, default: Any = None) -> Any:
            if isinstance(row, Mapping):
                return row.get(name, default)
            return getattr(row, name, default)

        candle_time = get("time", get("candle_time", get("timestamp")))
        if candle_time is None:
            raise ValueError("Candle is missing its time")

        required = ("open", "high", "low", "close")
        values = {name: get(name) for name in required}
        missing = [name for name, value in values.items() if value is None]
        if missing:
            raise ValueError(f"Candle is missing fields: {', '.join(missing)}")

        return CandleInput(
            time=int(candle_time),
            open=float(values["open"]),
            high=float(values["high"]),
            low=float(values["low"]),
            close=float(values["close"]),
            tick_volume=(
                int(get("tick_volume"))
                if get("tick_volume") is not None
                else None
            ),
        )

    def calculate(
        self,
        indicator: Indicator,
        candles: Sequence[Any],
        *,
        parameters: Mapping[str, Any] | None = None,
    ) -> list[IndicatorOutput]:
        resolved = indicator.validate_parameters(dict(parameters or {}))
        prepared = [self._to_candle(row) for row in candles]

        if not prepared:
            return []

        outputs = indicator.calculate(prepared, resolved)
        if not isinstance(outputs, Sequence):
            raise TypeError("Indicator.calculate() must return a sequence")

        for output in outputs:
            if not isinstance(output, IndicatorOutput):
                raise TypeError(
                    "Indicator.calculate() must return IndicatorOutput objects"
                )

        return list(outputs)
