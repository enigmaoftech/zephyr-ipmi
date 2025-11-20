"""Application configuration and settings management."""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parent.parent / ".." / ".env"),
        env_file_encoding="utf-8",
        env_prefix="ZEPHYR_",
        extra="ignore",
        env_nested_delimiter="__",
    )

    app_name: str = "Zephyr IPMI"
    secret_key: str = "change-me"
    encryption_key: str | None = None

    # Database
    database_url: str = "sqlite+aiosqlite:///./zephyr.db"

    # Security
    access_token_expire_minutes: int = 60 * 24
    allowed_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://localhost:5173",
        "https://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        "https://127.0.0.1:3000",
    ]
    session_cookie_secure: bool = True  # Force secure cookies for HTTPS

    # SSL/TLS
    ssl_cert_file: str | None = None
    ssl_key_file: str | None = None
    ssl_enabled: bool = False

    # Scheduler
    jobstore_url: str | None = None
    default_poll_interval_seconds: int = 300  # 5 minutes

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: List[str] | str) -> List[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return memoized settings instance."""

    return Settings()


settings = get_settings()
