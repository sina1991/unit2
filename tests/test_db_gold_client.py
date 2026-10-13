import httpx
import pytest

from app.clients.db_gold import DbGoldAPIError, DbGoldClient
from app.config import Settings


CANDLE = {
    "time": 1791579360,
    "open": 4194.662,
    "high": 4195.349,
    "low": 4194.499,
    "close": 4195.159,
    "tick_volume": 85,
    "spread": None,
    "real_volume": None,
}


def make_client(handler):
    settings = Settings(db_gold_api_base_url="http://db-gold.test")
    transport = httpx.MockTransport(handler)
    return DbGoldClient(settings=settings, transport=transport)


def test_fetch_candles_parses_documented_response():
    def handler(request):
        assert request.url.path == "/api/v1/candles"
        assert request.url.params["limit"] == "1"
        return httpx.Response(200, json={
            "symbol": "XAUUSD",
            "interval": "1m",
            "count": 1,
            "returned": 1,
            "candles": [CANDLE],
        })

    with make_client(handler) as client:
        result = client.fetch_candles(limit=1)

    assert result.candles[0].time == CANDLE["time"]
    assert result.candles[0].spread is None


def test_fetch_latest_parses_documented_response():
    def handler(request):
        assert request.url.path == "/api/v1/candles/latest"
        return httpx.Response(200, json={
            "symbol": "XAUUSD",
            "interval": "1m",
            "candle": CANDLE,
        })

    with make_client(handler) as client:
        result = client.fetch_latest()

    assert result.close == CANDLE["close"]


def test_http_error_is_wrapped():
    def handler(request):
        return httpx.Response(503, json={"detail": "unavailable"})

    with make_client(handler) as client:
        with pytest.raises(DbGoldAPIError, match="HTTP request failed"):
            client.fetch_candles(limit=1)


def test_invalid_limit_is_rejected_before_request():
    def handler(request):
        pytest.fail("HTTP request should not be sent")

    with make_client(handler) as client:
        with pytest.raises(ValueError, match="limit"):
            client.fetch_candles(limit=1001)


def test_unsupported_series_is_rejected():
    def handler(request):
        pytest.fail("HTTP request should not be sent")

    with make_client(handler) as client:
        with pytest.raises(ValueError, match="only XAUUSD"):
            client.fetch_candles(symbol="EURUSD")
