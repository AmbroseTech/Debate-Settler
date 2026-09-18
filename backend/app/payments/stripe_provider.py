"""Stripe card adapter (§32).

Uses the Stripe REST API with the secret key from environment only. Does not
assume Stripe supports every country/account type — enablement is controlled by
the registry + provider configuration. Never fakes success.
"""
from __future__ import annotations

import hmac
import hashlib
from typing import Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.payments.base import (
    PaymentProviderAdapter,
    PaymentResult,
    PaymentResultStatus,
    ProviderContext,
)

logger = get_logger(__name__)


class StripeProvider(PaymentProviderAdapter):
    code = "stripe"
    display_name = "Visa / Mastercard (Stripe)"
    kind = "card"
    supports_deposit = True
    supports_payout = True

    def _is_configured(self) -> bool:
        return bool(settings.STRIPE_SECRET_KEY)

    def _auth(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}"}

    async def create_deposit(self, ctx: ProviderContext) -> PaymentResult:
        if not self._is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="Stripe not configured.")
        # A real integration creates a PaymentIntent; client confirms on frontend.
        data = {
            "amount": str(int(ctx.amount * 100)),  # minor units
            "currency": ctx.currency.lower(),
            "automatic_payment_methods[enabled]": "true",
            "metadata[reference]": ctx.reference or "",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.stripe.com/v1/payment_intents", data=data, headers=self._auth()
                )
            body = resp.json() if resp.content else {}
            if resp.status_code == 200:
                return PaymentResult(
                    status=PaymentResultStatus.pending,
                    provider_reference=body.get("id"),
                    message="Payment intent created. Confirm to complete.",
                    raw=body,
                )
            return PaymentResult(status=PaymentResultStatus.failed, message="Could not start payment.")
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.failed, message="Could not reach Stripe.")

    async def verify_payment(self, provider_reference: str) -> PaymentResult:
        if not self._is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="Stripe not configured.")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"https://api.stripe.com/v1/payment_intents/{provider_reference}", headers=self._auth()
                )
            body = resp.json() if resp.content else {}
            status = body.get("status")
            mapping = {
                "succeeded": PaymentResultStatus.completed,
                "requires_payment_method": PaymentResultStatus.failed,
                "canceled": PaymentResultStatus.failed,
            }
            return PaymentResult(
                status=mapping.get(status, PaymentResultStatus.pending),
                provider_reference=provider_reference,
                raw=body,
            )
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.pending, message="Verification pending.")

    async def create_payout(self, ctx: ProviderContext) -> PaymentResult:
        # Payouts require Stripe Connect with a properly onboarded account.
        return PaymentResult(
            status=PaymentResultStatus.failed,
            message="Payouts require a configured Stripe Connect account.",
        )

    async def check_payout_status(self, provider_reference: str) -> PaymentResult:
        return PaymentResult(status=PaymentResultStatus.pending, message="Not implemented.")

    async def handle_webhook(self, payload: bytes, headers: Dict[str, str]) -> PaymentResult:
        signature = headers.get("stripe-signature", "")
        if not self._verify_signature(payload, signature, settings.STRIPE_WEBHOOK_SECRET):
            logger.warning("stripe_webhook_signature_invalid")
            return PaymentResult(status=PaymentResultStatus.failed, message="Invalid signature.")
        import json

        try:
            event = json.loads(payload.decode())
        except (ValueError, UnicodeDecodeError):
            return PaymentResult(status=PaymentResultStatus.failed, message="Invalid payload.")
        event_type = event.get("type", "")
        data_obj = event.get("data", {}).get("object", {})
        status = PaymentResultStatus.completed if event_type.endswith(".succeeded") else PaymentResultStatus.pending
        return PaymentResult(
            status=status,
            provider_reference=data_obj.get("id"),
            message=event_type,
            raw=event,
        )

    @staticmethod
    def _verify_signature(payload: bytes, header: str, secret: str) -> bool:
        if not secret or not header:
            return False
        # Stripe-Signature: t=<timestamp>,v1=<sig>
        parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
        timestamp = parts.get("t", "")
        expected = parts.get("v1", "")
        signed = f"{timestamp}.{payload.decode('utf-8', 'ignore')}".encode()
        computed = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, expected)
