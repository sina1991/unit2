from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from app.config import Settings, get_settings


class DbGoldAPIError(RuntimeError):
    """Raised when db-gold cannot provide a valid API response."""


class Candle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    time: int
    open: float
    high: float
    low: float
    close: float
    tick_volume: int | None = None
    spread: int | None = None
    real_volume: int | None = None


class CandlesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    interval: str
    count: int
    returned: int
    candles: list[Candle]


class LatestCandleResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    interval: str
    candle: Candle


class DbGoldClient:
    """HTTP-only client for the documented db-gold candle API."""

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        config = settings or get_settings()
        self._client = httpx.Client(
            base_url=config.db_gold_api_base_url.rstrip("/"),
            timeout=config.http_timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DbGoldClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise DbGoldAPIError("db-gold returned a non-object JSON response")
            return payload
        except httpx.HTTPError as exc:
            raise DbGoldAPIError(f"db-gold HTTP request failed: {exc}") from exc
        except ValueError as exc:
            raise DbGoldAPIError("db-gold returned invalid JSON") from exc

    @staticmethod
    def _validate_series(symbol: str, interval: str) -> None:
        if symbol != "XAUUSD" or interval != "1m":
            raise ValueError("This service supports only XAUUSD candles at 1m")

    def fetch_candles(
        self,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
        symbol: str = "XAUUSD",
        interval: str = "1m",
    ) -> CandlesResponse:
        self._validate_series(symbol, interval)

        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        if start_time is not None and end_time is not None:
            if start_time > end_time:
                raise ValueError("start_time must not exceed end_time")

        params: dict[str, Any] = {"limit": limit}
        if start_time is not None:
            params["start_time"] = start_time
        if end_time is not None:
            params["end_time"] = end_time

        try:
            result = CandlesResponse.model_validate(
                self._get_json("/api/v1/candles", params)
            )
        except ValidationError as exc:
            raise DbGoldAPIError(
                f"db-gold candle response does not match the expected schema: {exc}"
            ) from exc

        if result.symbol != symbol or result.interval != interval:
            raise DbGoldAPIError("db-gold returned an unexpected symbol or interval")
        if result.returned != len(result.candles):
            raise DbGoldAPIError("db-gold returned count does not match candle list")
        return result

    def fetch_latest(
        self,
        symbol: str = "XAUUSD",
        interval: str = "1m",
    ) -> Candle:
        self._validate_series(symbol, interval)

        try:
            result = LatestCandleResponse.model_validate(
                self._get_json("/api/v1/candles/latest", {})
            )
        except ValidationError as exc:
            raise DbGoldAPIError(
                f"db-gold latest response does not match the expected schema: {exc}"
            ) from exc

        if result.symbol != symbol or result.interval != interval:
            raise DbGoldAPIError("db-gold returned an unexpected symbol or interval")
        return result.candle
