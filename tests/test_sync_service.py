from types import SimpleNamespace

import pytest

from app.clients.db_gold import Candle
from app.database.core import connect, initialize
import app.sync_service as sync_module


@pytest.fixture
def sync_db(tmp_path, monkeypatch):
    db_path = tmp_path / "analytics.db"
    initialize(db_path)
    monkeypatch.setattr(
        sync_module, "connect_configured", lambda: connect(db_path)
    )
    monkeypatch.setattr(
        sync_module, "initialize_configured", lambda: initialize(db_path)
    )
    return db_path


class FakeClient:
    def __init__(self, candles, fail=False):
        self.candles = candles
        self.fail = fail
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def fetch_candles(
        self, limit, start_time=None, end_time=None,
        symbol="XAUUSD", interval="1m",
    ):
        self.calls.append((start_time, end_time))
        if self.fail:
            raise RuntimeError("simulated API failure")
        selected = [
            candle for candle in self.candles
            if (start_time is None or candle.time >= start_time)
            and (end_time is None or candle.time <= end_time)
        ]
        selected.sort(key=lambda candle: candle.time)
        return SimpleNamespace(candles=selected[-limit:])


def make_candles(count=5):
    return [
        Candle(
            time=60 * (i + 1),
            open=100 + i,
            high=101 + i,
            low=99 + i,
            close=100.5 + i,
            tick_volume=10,
            spread=None,
            real_volume=None,
        )
        for i in range(count)
    ]


def install_client(monkeypatch, client):
    monkeypatch.setattr(
        sync_module, "DbGoldClient", lambda settings=None: client
    )


def test_sync_pages_through_history_and_records_run(sync_db, monkeypatch):
    client = FakeClient(make_candles())
    install_client(monkeypatch, client)

    result = sync_module.sync_candles(batch_size=2)

    assert result["status"] == "succeeded"
    assert result["fetched_count"] == 5
    assert len(client.calls) >= 3

    with connect(sync_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 5
        run = connection.execute(
            "SELECT status, fetched_count FROM sync_runs WHERE run_id = ?",
            (result["run_id"],),
        ).fetchone()
        assert run["status"] == "succeeded"
        assert run["fetched_count"] == 5


def test_repeat_sync_does_not_duplicate_candles(sync_db, monkeypatch):
    candles = make_candles()
    first_client = FakeClient(candles)
    install_client(monkeypatch, first_client)
    sync_module.sync_candles(batch_size=2)

    second_client = FakeClient(candles)
    install_client(monkeypatch, second_client)
    result = sync_module.sync_candles(batch_size=2)

    assert result["status"] == "succeeded"
    with connect(sync_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 5


def test_api_failure_is_recorded(sync_db, monkeypatch):
    install_client(monkeypatch, FakeClient([], fail=True))

    with pytest.raises(RuntimeError, match="Sync failed"):
        sync_module.sync_candles(batch_size=2)

    with connect(sync_db) as connection:
        run = connection.execute(
            "SELECT status, error_details FROM sync_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        assert run["status"] == "failed"
        assert "simulated API failure" in run["error_details"]
