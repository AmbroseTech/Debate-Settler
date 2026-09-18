"""Demo payment provider (§39).

Fully functional simulation for development. Every result is clearly marked as
DEMO and never moves real money. It can simulate success, pending and failure
so the whole financial flow can be exercised end-to-end.
"""
from __future__ import annotations

import hashlib
from typing import Dict

from app.payments.base import (
    PaymentProviderAdapter,
    PaymentResult,
    PaymentResultStatus,
    ProviderContext,
)


class DemoProvider(PaymentProviderAdapter):
    code = "demo"
    display_name = "Demo Funds (No Real Money)"
    kind = "demo"
    is_demo = True
    supports_deposit = True
    supports_payout = True

    @staticmethod
    def _decide(reference: str) -> PaymentResultStatus:
        # Deterministic simulation: destinations ending in an odd digit fail so
        # developers can test failure paths. Everything else succeeds.
        digest = hashlib.sha256(reference.encode()).hexdigest()
        if digest.endswith("f"):
            return PaymentResultStatus.failed
        return PaymentResultStatus.completed

    async def create_deposit(self, ctx: ProviderContext) -> PaymentResult:
        ref = f"DEMO-DEP-{ctx.reference}"
        status = self._decide(ref)
        return PaymentResult(
            status=status,
            provider_reference=ref,
            message="DEMO FUNDS — simulated deposit, no real money moved.",
        )

    async def verify_payment(self, provider_reference: str) -> PaymentResult:
        return PaymentResult(
            status=PaymentResultStatus.completed,
            provider_reference=provider_reference,
            message="DEMO FUNDS — simulated verification.",
        )

    async def create_payout(self, ctx: ProviderContext) -> PaymentResult:
        ref = f"DEMO-WD-{ctx.reference}"
        status = self._decide(ref)
        return PaymentResult(
            status=status,
            provider_reference=ref,
            message="DEMO FUNDS — simulated withdrawal, no real money moved.",
        )

    async def check_payout_status(self, provider_reference: str) -> PaymentResult:
        return PaymentResult(
            status=PaymentResultStatus.completed,
            provider_reference=provider_reference,
            message="DEMO FUNDS — simulated payout status.",
        )

    async def handle_webhook(self, payload: bytes, headers: Dict[str, str]) -> PaymentResult:
        return PaymentResult(
            status=PaymentResultStatus.completed,
            message="DEMO FUNDS — simulated webhook.",
        )
