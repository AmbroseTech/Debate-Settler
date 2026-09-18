"""PayPal adapter (§32).

PayPal is not available in every country — enablement is controlled by the
registry. Credentials come from environment only.
"""
from __future__ import annotations

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

BASE = "https://api-m.paypal.com"


class PayPalProvider(PaymentProviderAdapter):
    code = "paypal"
    display_name = "PayPal"
    kind = "wallet"
    supports_deposit = True
    supports_payout = True

    def _is_configured(self) -> bool:
        return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)

    async def _token(self, client: httpx.AsyncClient) -> Optional[str]:
        try:
            resp = await client.post(
                f"{BASE}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
            )
            return resp.json().get("access_token") if resp.content else None
        except httpx.HTTPError:
            return None

    async def create_deposit(self, ctx: ProviderContext) -> PaymentResult:
        if not self._is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="PayPal not configured.")
        body = {
            "intent": "CAPTURE",
            "purchase_units": [
                {"amount": {"currency_code": ctx.currency, "value": str(ctx.amount)},
                 "reference_id": ctx.reference}
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                token = await self._token(client)
                resp = await client.post(
                    f"{BASE}/v2/checkout/orders",
                    json=body,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
            data = resp.json() if resp.content else {}
            if resp.status_code == 201:
                return PaymentResult(
                    status=PaymentResultStatus.pending,
                    provider_reference=data.get("id"),
                    message="PayPal order created. Approve to complete.",
                    raw=data,
                )
            return PaymentResult(status=PaymentResultStatus.failed, message="Could not create PayPal order.")
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.failed, message="Could not reach PayPal.")

    async def verify_payment(self, provider_reference: str) -> PaymentResult:
        if not self._is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="PayPal not configured.")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                token = await self._token(client)
                resp = await client.get(
                    f"{BASE}/v2/checkout/orders/{provider_reference}",
                    headers={"Authorization": f"Bearer {token}"},
                )
            data = resp.json() if resp.content else {}
            status = (data.get("status") or "").upper()
            mapping = {
                "COMPLETED": PaymentResultStatus.completed,
                "APPROVED": PaymentResultStatus.pending,
                "VOIDED": PaymentResultStatus.failed,
            }
            return PaymentResult(
                status=mapping.get(status, PaymentResultStatus.pending),
                provider_reference=provider_reference,
                raw=data,
            )
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.pending, message="Verification pending.")

    async def create_payout(self, ctx: ProviderContext) -> PaymentResult:
        if not self._is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="PayPal not configured.")
        body = {
            "sender_batch_header": {"sender_batch_id": ctx.reference, "email_subject": "You received a payment"},
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {"value": str(ctx.amount), "currency": ctx.currency},
                    "receiver": ctx.destination,
                    "note": "Debate_Settler withdrawal",
                }
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                token = await self._token(client)
                resp = await client.post(
                    f"{BASE}/v1/payments/payouts",
                    json=body,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
            data = resp.json() if resp.content else {}
            if resp.status_code in (200, 201):
                return PaymentResult(
                    status=PaymentResultStatus.pending,
                    provider_reference=data.get("batch_header", {}).get("payout_batch_id"),
                    message="Payout submitted. Awaiting confirmation.",
                )
            return PaymentResult(status=PaymentResultStatus.failed, message="Payout request failed.")
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.failed, message="Could not reach PayPal.")

    async def check_payout_status(self, provider_reference: str) -> PaymentResult:
        if not self._is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="PayPal not configured.")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                token = await self._token(client)
                resp = await client.get(
                    f"{BASE}/v1/payments/payouts/{provider_reference}",
                    headers={"Authorization": f"Bearer {token}"},
                )
            data = resp.json() if resp.content else {}
            status = (data.get("batch_status") or "").upper()
            mapping = {
                "SUCCESS": PaymentResultStatus.completed,
                "PENDING": PaymentResultStatus.pending,
                "DENIED": PaymentResultStatus.failed,
                "CANCELLED": PaymentResultStatus.failed,
            }
            return PaymentResult(
                status=mapping.get(status, PaymentResultStatus.pending),
                provider_reference=provider_reference,
                raw=data,
            )
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.pending, message="Status pending.")

    async def handle_webhook(self, payload: bytes, headers: Dict[str, str]) -> PaymentResult:
        # Verify using PayPal's /v1/notifications/verify-webhook-signature in production.
        import json

        try:
            event = json.loads(payload.decode())
        except (ValueError, UnicodeDecodeError):
            return PaymentResult(status=PaymentResultStatus.failed, message="Invalid payload.")
        event_type = event.get("event_type", "")
        status = PaymentResultStatus.completed if event_type.endswith(".COMPLETED") else PaymentResultStatus.pending
        return PaymentResult(
            status=status,
            provider_reference=event.get("resource", {}).get("id"),
            message=event_type,
            raw=event,
        )
