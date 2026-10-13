from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class IndicatorMetadata:
    identifier: str
    display_name: str
    implementation_version: str
    description: str
    default_parameters: Mapping[str, Any]
    required_lookback: int


@dataclass(frozen=True)
class CandleInput:
    time: int
    open: float
    high: float
    low: float
    close: float
    tick_volume: int | None = None


@dataclass(frozen=True)
class IndicatorOutput:
    time: int
    values: Mapping[str, float | None]


class Indicator(ABC):
    """Contract implemented by explicitly trusted indicator plugins."""

    @property
    @abstractmethod
    def metadata(self) -> IndicatorMetadata:
        """Return stable metadata and default parameters."""
        raise NotImplementedError

    @abstractmethod
    def calculate(
        self,
        candles: Sequence[CandleInput],
        parameters: Mapping[str, Any],
    ) -> Sequence[IndicatorOutput]:
        """Calculate outputs aligned to candle timestamps."""
        raise NotImplementedError

    def validate_parameters(
        self,
        parameters: Mapping[str, Any],
    ) -> dict[str, Any]:
        defaults = dict(self.metadata.default_parameters)
        unknown = set(parameters) - set(defaults)

        if unknown:
            raise ValueError(
                f"Unsupported parameters: {', '.join(sorted(unknown))}"
            )

        resolved = {**defaults, **parameters}

        for name, value in resolved.items():
            if isinstance(value, bool):
                raise ValueError(f"Invalid parameter: {name}")
            if not isinstance(value, (int, float, str)):
                raise ValueError(f"Invalid parameter: {name}")

        return resolved
