from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_gold_api_base_url: str = "http://127.0.0.1:8000"
    analytics_database_path: str = "data/analytics.db"
    analytics_host: str = "127.0.0.1"
    analytics_port: int = Field(default=8001, ge=1, le=65535)
    http_timeout_seconds: float = Field(default=10.0, gt=0)
    sync_batch_size: int = Field(default=500, ge=1, le=1000)
    log_level: str = "INFO"
    indicator_paths: str = "app/indicators/plugins"
    script_paths: str = "scripts"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_database_path(settings: Settings | None = None) -> Path:
    current = settings or get_settings()
    path = Path(current.analytics_database_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path
