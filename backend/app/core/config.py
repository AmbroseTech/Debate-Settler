"""Application configuration.

All configuration is driven by environment variables so that no secrets are
ever hard-coded. See `.env.example` at the repository root for the full list.
"""
from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # root of the project
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
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
    DATABASE_URL: str 
    SYNC_DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Security ---
    SECRET_KEY: str = "change-me-in-production"
    JWT_SECRET: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # --- Compliance / feature flags ---
    # These control whether financially-sensitive features are available.
    ENABLE_REAL_MONEY: bool = False
    ENABLE_LOCAL_MONEY: bool = False
    ENABLE_WITHDRAWALS: bool = False
    ENABLE_GAMES: bool = True
    REQUIRE_KYC: bool = False
    REQUIRE_AGE_VERIFICATION: bool = False

    # --- Financial configuration ---
    DEFAULT_CURRENCY: str = "UGX"
    # Platform settlement fee is configurable (percentage). Business/legal may
    # set this anywhere within PLATFORM_FEE_MIN..PLATFORM_FEE_MAX.
    PLATFORM_FEE_PERCENT: Decimal = Decimal("5.00")
    PLATFORM_FEE_MIN: Decimal = Decimal("0.00")
    PLATFORM_FEE_MAX: Decimal = Decimal("10.00")
    WITHDRAWAL_FEE_PERCENT: Decimal = Decimal("1.00")
    FUNDING_TIMEOUT_MINUTES: int = 60

    # --- Payment providers (only include what is configured) ---
    PAYMENT_MODE: str = "demo"  # demo | live
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_WEBHOOK_ID: str = ""
    MTN_API_KEY: str = ""
    MTN_API_SECRET: str = ""
    MTN_BASE_URL: str = "https://sandbox.momodeveloper.mtn.com"
    AIRTEL_API_KEY: str = ""
    AIRTEL_API_SECRET: str = ""
    AIRTEL_BASE_URL: str = "https://openapiuat.airtel.africa"

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

    @property
    def platform_fee_fraction(self) -> Decimal:
        return self.PLATFORM_FEE_PERCENT / Decimal(100)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
