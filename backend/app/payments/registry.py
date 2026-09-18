"""Payment provider registry (§33, §34).

Selects which providers are available based on country, currency and
configuration. In demo mode (or when real money is disabled) only the demo
provider is offered, so simulated transactions never look real.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.core.config import settings
from app.payments.airtel import AirtelProvider
from app.payments.base import PaymentProviderAdapter
from app.payments.demo import DemoProvider
from app.payments.mtn import MTNProvider
from app.payments.paypal import PayPalProvider
from app.payments.stripe_provider import StripeProvider

_REGISTRY: Dict[str, PaymentProviderAdapter] = {}


def _build_registry() -> Dict[str, PaymentProviderAdapter]:
    global _REGISTRY
    if not _REGISTRY:
        providers: List[PaymentProviderAdapter] = [
            DemoProvider(),
            MTNProvider(),
            AirtelProvider(),
            StripeProvider(),
            PayPalProvider(),
        ]
        _REGISTRY = {p.code: p for p in providers}
    return _REGISTRY


def get_provider(code: str) -> Optional[PaymentProviderAdapter]:
    return _build_registry().get(code)


def real_money_enabled() -> bool:
    return settings.ENABLE_REAL_MONEY and settings.PAYMENT_MODE == "live"


def available_providers(
    country_code: Optional[str] = None,
    currency: Optional[str] = None,
    *,
    for_payout: bool = False,
) -> List[PaymentProviderAdapter]:
    """Return providers a given user may actually use.

    Only demo funds are offered unless real money is enabled — this keeps
    simulated transactions from masquerading as real payments.
    """
    registry = _build_registry()
    if not real_money_enabled():
        return [registry["demo"]]

    result: List[PaymentProviderAdapter] = []
    for provider in registry.values():
        if provider.is_demo:
            continue
        if for_payout and not provider.supports_payout:
            continue
        allowed_countries = provider.countries()
        if allowed_countries and country_code and country_code not in allowed_countries:
            continue
        # Mobile money only for UG; cards/wallets elsewhere.
        if provider.kind == "mobile_money" and country_code and country_code != "UG":
            continue
        result.append(provider)
    return result


def resolve_provider(code: str, country_code: Optional[str] = None, *, for_payout: bool = False) -> Optional[PaymentProviderAdapter]:
    allowed = {p.code for p in available_providers(country_code, for_payout=for_payout)}
    provider = get_provider(code)
    if provider is None or provider.code not in allowed:
        return None
    return provider
