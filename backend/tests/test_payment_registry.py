"""Provider availability must fail closed on production configurations."""

import pytest

from app.core.config import settings
from app.db.seed import run_seed
from app.payments.registry import available_providers, resolve_provider


def test_demo_provider_is_not_exposed_in_production(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "ENABLE_REAL_MONEY", False)
    monkeypatch.setattr(settings, "PAYMENT_MODE", "demo")

    assert available_providers("UG") == []
    assert resolve_provider("demo", "UG") is None


def test_airtel_is_not_exposed_when_live_providers_are_listed(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "ENABLE_REAL_MONEY", True)
    monkeypatch.setattr(settings, "PAYMENT_MODE", "live")

    providers = available_providers("UG")

    assert "airtel" not in {provider.code for provider in providers}
    assert resolve_provider("airtel", "UG") is None


def test_airtel_collections_require_credentials_and_production_base_url(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "ENABLE_REAL_MONEY", True)
    monkeypatch.setattr(settings, "PAYMENT_MODE", "live")
    monkeypatch.setattr(settings, "AIRTEL_API_KEY", "test-client-id")
    monkeypatch.setattr(settings, "AIRTEL_API_SECRET", "test-client-secret")
    monkeypatch.setattr(settings, "AIRTEL_BASE_URL", "https://airtel-live.example")
    monkeypatch.setattr(settings, "AIRTEL_ENABLED", False)

    assert resolve_provider("airtel", "UG") is None

    monkeypatch.setattr(settings, "AIRTEL_ENABLED", True)

    provider = resolve_provider("airtel", "UG")

    assert provider is not None
    assert provider.supports_deposit is True
    assert provider.supports_payout is False


def test_airtel_uat_url_is_not_advertised_in_production(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "ENABLE_REAL_MONEY", True)
    monkeypatch.setattr(settings, "PAYMENT_MODE", "live")
    monkeypatch.setattr(settings, "AIRTEL_API_KEY", "test-client-id")
    monkeypatch.setattr(settings, "AIRTEL_API_SECRET", "test-client-secret")
    monkeypatch.setattr(settings, "AIRTEL_BASE_URL", "https://openapiuat.airtel.africa")
    monkeypatch.setattr(settings, "AIRTEL_ENABLED", True)

    assert resolve_provider("airtel", "UG") is None


async def test_demo_seed_refuses_to_run_in_production(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")

    with pytest.raises(RuntimeError, match="disabled in production"):
        await run_seed()
