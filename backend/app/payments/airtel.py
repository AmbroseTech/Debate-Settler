"""Airtel Money adapter (Uganda) (§31).

Mirrors the MTN adapter. Uses official Airtel Open API with credentials from
environment only. Never fakes a successful payment.
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


class AirtelProvider(PaymentProviderAdapter):
    code = "airtel"
    display_name = "Airtel Money"
    kind = "mobile_money"
    supports_deposit = True
    # Enable collections only. Payouts stay off until the Airtel account's
    # disbursement product and status flow have been verified.
    supports_payout = False

    def countries(self) -> Optional[list[str]]:
        return ["UG"]

    def is_configured(self) -> bool:
        configured = bool(
            settings.AIRTEL_ENABLED
            and settings.AIRTEL_API_KEY
            and settings.AIRTEL_API_SECRET
        )
        # Never accidentally send a production customer to the UAT host.
        if settings.APP_ENV == "production" and "uat" in settings.AIRTEL_BASE_URL.lower():
            return False
        return configured and bool(settings.AIRTEL_BASE_URL)

    async def _token(self, client: httpx.AsyncClient) -> Optional[str]:
        try:
            resp = await client.post(
                f"{settings.AIRTEL_BASE_URL}/auth/oauth2/token",
                data={
                    "client_id": settings.AIRTEL_API_KEY,
                    "client_secret": settings.AIRTEL_API_SECRET,
                    "grant_type": "client_credentials",
                },
            )
            return resp.json().get("access_token") if resp.content else None
        except httpx.HTTPError:
            return None

    async def create_deposit(self, ctx: ProviderContext) -> PaymentResult:
        if not self.is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="Airtel not configured.")
        body = {
            "reference": ctx.reference,
            "subscriber": {"country": "UG", "currency": ctx.currency, "msisdn": ctx.destination},
            "transaction": {"amount": str(ctx.amount), "country": "UG", "currency": ctx.currency, "id": ctx.reference},
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                token = await self._token(client)
                resp = await client.post(
                    f"{settings.AIRTEL_BASE_URL}/merchant/v1/payments/",
                    json=body,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
            if resp.status_code in (200, 201, 202):
                data = resp.json() if resp.content else {}
                return PaymentResult(
                    status=PaymentResultStatus.pending,
                    provider_reference=data.get("data", {}).get("transaction_id"),
                    message="Deposit request submitted. Awaiting confirmation.",
                    raw=data,
                )
            return PaymentResult(status=PaymentResultStatus.failed, message="Deposit request failed.")
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.failed, message="Could not reach Airtel.")

    async def verify_payment(self, provider_reference: str) -> PaymentResult:
        if not self.is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="Airtel not configured.")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                token = await self._token(client)
                resp = await client.get(
                    f"{settings.AIRTEL_BASE_URL}/merchant/v1/payments/{provider_reference}",
                    headers={"Authorization": f"Bearer {token}"},
                )
            data = resp.json().get("data", {}) if resp.content else {}
            status = (data.get("transaction_status") or "").lower()
            mapping = {
                "successful": PaymentResultStatus.completed,
                "success": PaymentResultStatus.completed,
                "pending": PaymentResultStatus.pending,
                "failed": PaymentResultStatus.failed,
            }
            return PaymentResult(
                status=mapping.get(status, PaymentResultStatus.pending),
                provider_reference=provider_reference,
                raw=data,
            )
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.pending, message="Verification pending.")

    async def create_payout(self, ctx: ProviderContext) -> PaymentResult:
        if not self.is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="Airtel not configured.")
        body = {
            "reference": ctx.reference,
            "transfer": {
                "amount": str(ctx.amount),
                "currency": ctx.currency,
                "type": "B2C",
                "beneficiary_country": "UG",
            },
            "payee": {"is_msisdn": True, "msisdn": ctx.destination},
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                token = await self._token(client)
                resp = await client.post(
                    f"{settings.AIRTEL_BASE_URL}/merchant/v1/disbursements/",
                    json=body,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
            if resp.status_code in (200, 201, 202):
                data = resp.json() if resp.content else {}
                return PaymentResult(
                    status=PaymentResultStatus.pending,
                    provider_reference=data.get("data", {}).get("transaction_id"),
                    message="Withdrawal submitted. Awaiting confirmation.",
                )
            return PaymentResult(status=PaymentResultStatus.failed, message="Withdrawal request failed.")
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.failed, message="Could not reach Airtel.")

    async def check_payout_status(self, provider_reference: str) -> PaymentResult:
        if not self.is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="Airtel not configured.")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                token = await self._token(client)
                resp = await client.get(
                    f"{settings.AIRTEL_BASE_URL}/merchant/v1/disbursements/{provider_reference}",
                    headers={"Authorization": f"Bearer {token}"},
                )
            data = resp.json().get("data", {}) if resp.content else {}
            status = (data.get("transaction_status") or "").lower()
            mapping = {
                "successful": PaymentResultStatus.completed,
                "success": PaymentResultStatus.completed,
                "pending": PaymentResultStatus.pending,
                "failed": PaymentResultStatus.failed,
            }
            return PaymentResult(
                status=mapping.get(status, PaymentResultStatus.pending),
                provider_reference=provider_reference,
                raw=data,
            )
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.pending, message="Status pending.")

    async def handle_webhook(self, payload: bytes, headers: Dict[str, str]) -> PaymentResult:
        import json

        try:
            data = json.loads(payload.decode())
        except (ValueError, UnicodeDecodeError):
            return PaymentResult(status=PaymentResultStatus.failed, message="Invalid webhook payload.")
        return PaymentResult(
            status=PaymentResultStatus.pending,
            provider_reference=data.get("reference"),
            message="Webhook received; verifying with provider.",
            raw=data,
        )
