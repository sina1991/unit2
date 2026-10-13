"""Coordinate historical and incremental indicator calculations."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from app.indicators.base import Indicator
from app.indicators.candle_loader import CandleLoader
from app.indicators.engine import IndicatorEngine
from app.indicators.results import save_indicator_outputs


class IndicatorService:
    """Coordinate loading, calculation and persistence for one configured instance.

    The caller is responsible for saving and restoring the online checkpoint.
    Call run_historical for backfill and run_online for newer candles.
    """

    def __init__(
        self,
        *,
        indicator: Indicator,
        indicator_id: str,
        parameter_set_id: str,
        parameters: Mapping[str, Any] | None = None,
        calculation_version: str = "1",
        loader: CandleLoader | None = None,
        engine: IndicatorEngine | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        if not indicator_id or not parameter_set_id or not calculation_version:
            raise ValueError(
                "indicator_id, parameter_set_id and calculation_version are required"
            )

        self.indicator = indicator
        self.indicator_id = indicator_id
        self.parameter_set_id = parameter_set_id
        self.parameters = indicator.validate_parameters(dict(parameters or {}))
        self.calculation_version = calculation_version
        self.connection = connection
        self.loader = loader or CandleLoader(connection=connection)
        self.engine = engine or IndicatorEngine()

    def _calculate_and_save(
        self,
        candles: list[dict[str, Any]],
        *,
        symbol: str,
        interval: str,
    ) -> int:
        outputs = self.engine.calculate(
            self.indicator,
            candles,
            parameters=self.parameters,
        )
        return save_indicator_outputs(
            outputs,
            symbol=symbol,
            interval=interval,
            indicator_id=self.indicator_id,
            parameter_set_id=self.parameter_set_id,
            calculation_version=self.calculation_version,
            connection=self.connection,
        )

    def run_historical(
        self,
        symbol: str,
        interval: str,
        *,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> int:
        """Calculate the requested historical range and persist its outputs."""
        candles = self.loader.load(
            symbol,
            interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        return self._calculate_and_save(candles, symbol=symbol, interval=interval)

    def run_online(
        self,
        symbol: str,
        interval: str,
        *,
        after_candle_time: int,
        limit: int | None = None,
    ) -> int:
        """Calculate candles newer than a checkpoint supplied by the caller."""
        candles = self.loader.load_after(
            symbol,
            interval,
            after_candle_time,
            limit=limit,
        )
        return self._calculate_and_save(candles, symbol=symbol, interval=interval)
