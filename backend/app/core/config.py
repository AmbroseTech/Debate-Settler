"""Application configuration.

All configuration is driven by environment variables so that no secrets are
ever hard-coded. See `.env.example` at the repository root for the full list.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    APP_NAME: str = "Debate_Settler"
    APP_ENV: str = "development"  # development | staging | production
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # --- Database / cache ---
    DATABASE_URL: str = (
        "postgresql+asyncpg://ds:ds_password@localhost:5432/debate_settler"
    )
    SYNC_DATABASE_URL: str = (
        "postgresql+psycopg2://ds:ds_password@localhost:5432/debate_settler"
    )
    REDIS_URL: str = "redis://localhost:6379/0"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Security ---
    SECRET_KEY: str = "change-me-in-production"
    JWT_SECRET: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    ENABLE_GAMES: bool = True
    MAX_MEDIA_UPLOAD_MB: int = 25
    MAX_VIDEO_SECONDS: int = 120

    # --- Notifications ---
    EMAIL_API_KEY: str = ""
    EMAIL_FROM: str = "no-reply@debate-settler.local"
    SMS_API_KEY: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
