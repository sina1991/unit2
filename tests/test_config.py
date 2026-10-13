from pathlib import Path

from app.config import Settings, get_database_path


def test_database_path_is_resolved_from_project_root():
    settings = Settings(analytics_database_path="data/test-analytics.db")

    assert get_database_path(settings) == (
        Path(__file__).resolve().parents[1] / "data" / "test-analytics.db"
    )


def test_absolute_database_path_is_preserved(tmp_path):
    database = tmp_path / "analytics.db"
    settings = Settings(analytics_database_path=str(database))

    assert get_database_path(settings) == database


def test_sync_batch_size_cannot_exceed_api_limit():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(sync_batch_size=1001)
