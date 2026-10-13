import pytest
from fastapi.testclient import TestClient

from app.config import get_database_path
from app.database.core import initialize
from app.main import app


@pytest.fixture
def client_and_db(tmp_path, monkeypatch):
    db_path = tmp_path / "analytics-test.db"
    monkeypatch.setattr("app.config.get_database_path", lambda: db_path)
    initialize(db_path)

    with __import__("app.database.core", fromlist=["connect"]).connect(db_path) as conn:
        conn.execute(
            """INSERT INTO candles
               (symbol, interval, candle_time, open, high, low, close,
                tick_volume, spread, real_volume)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("XAUUSD", "1m", 1791579300, 4194.6, 4195.6, 4194.5, 4194.9, 119, None, None),
        )
        conn.execute(
            """INSERT INTO sync_runs
               (run_id, status, fetched_count, inserted_or_updated_count)
               VALUES (?, ?, ?, ?)""",
            ("test-run", "succeeded", 1, 1),
        )

    previous = getattr(app.state, "disable_worker", False)
    app.state.disable_worker = True

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.state.disable_worker = previous

def test_health(client_and_db):
    response = client_and_db.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_candles(client_and_db):
    response = client_and_db.get("/api/v1/candles?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["returned"] == 1
    assert body["candles"][0]["time"] == 1791579300


def test_latest_candle(client_and_db):
    response = client_and_db.get("/api/v1/candles/latest")
    assert response.status_code == 200
    assert response.json()["candle"]["close"] == pytest.approx(4194.9)


def test_latest_candle_not_found(tmp_path, monkeypatch):
    db_path = tmp_path / "empty.db"
    monkeypatch.setattr("app.config.get_database_path", lambda: db_path)
    initialize(db_path)
    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/candles/latest")
    assert response.status_code == 404


def test_sync_runs(client_and_db):
    response = client_and_db.get("/api/v1/sync-runs")
    assert response.status_code == 200
    assert response.json()["returned"] == 1
    assert response.json()["runs"][0]["run_id"] == "test-run"


def test_reject_unsupported_series(client_and_db):
    response = client_and_db.get("/api/v1/candles?symbol=EURUSD")
    assert response.status_code == 400


def test_reject_invalid_time_range(client_and_db):
    response = client_and_db.get(
        "/api/v1/candles?start_time=200&end_time=100"
    )
    assert response.status_code == 400
