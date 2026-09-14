"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "production", "test"] = "development"
    app_debug: bool = True
    app_timezone: str = "Asia/Kolkata"
    app_secret_key: str = "change-me"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # DB
    db_dialect: Literal["sqlite", "postgres"] = "sqlite"
    database_url: str = "sqlite:///./data/trading.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False

    # Market provider
    data_provider: Literal["demo", "kite", "groww"] = "demo"

    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""

    groww_api_key: str = ""
    groww_api_secret: str = ""
    groww_access_token: str = ""

    # Mock market
    mock_tick_interval_ms: int = 500
    mock_depth_levels: int = 25
    mock_seed: int = 42

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("database_url")
    @classmethod
    def _ensure_sqlite_dir(cls, v: str) -> str:
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
