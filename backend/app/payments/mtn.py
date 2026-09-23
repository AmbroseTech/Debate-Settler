"""MTN Mobile Money adapter (Uganda) (§31).

Production integration must use the official MTN MoMo API with a properly
configured merchant account. Credentials come from environment only. This
adapter never marks a payment complete merely because a request was submitted —
it returns `pending` and relies on `verify_payment`/webhooks for confirmation.
"""
from __future__ import annotations

import uuid
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


class MTNProvider(PaymentProviderAdapter):
    code = "mtn"
    display_name = "MTN Mobile Money"
    kind = "mobile_money"
    supports_deposit = True
    # Keep payouts unavailable until the account's disbursement credentials and
    # transaction verification flow have been confirmed for this deployment.
    supports_payout = False

    def countries(self) -> Optional[list[str]]:
        return ["UG"]

    def is_configured(self) -> bool:
        return bool(settings.MTN_API_KEY and settings.MTN_API_SECRET)

    async def _headers(self) -> Dict[str, str]:
        # In production, exchange credentials for an OAuth bearer token here.
        return {
            "Ocp-Apim-Subscription-Key": settings.MTN_API_KEY,
            "X-Reference-Id": str(uuid.uuid4()),
            "X-Target-Environment": "sandbox",
            "Content-Type": "application/json",
        }

    async def create_deposit(self, ctx: ProviderContext) -> PaymentResult:
        if not self.is_configured():
            return PaymentResult(
                status=PaymentResultStatus.failed,
                message="MTN provider is not configured.",
            )
        body = {
            "amount": str(ctx.amount),
            "currency": ctx.currency,
            "externalId": ctx.reference,
            "payer": {"partyIdType": "MSISDN", "partyId": (ctx.destination or "").lstrip("0")},
            "payerMessage": "Debate_Settler deposit",
            "payeeNote": "Deposit",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.MTN_BASE_URL}/collection/v1_0/requesttopay",
                    json=body,
                    headers=await self._headers(),
                )
            if resp.status_code in (200, 201, 202):
                return PaymentResult(
                    status=PaymentResultStatus.pending,
                    provider_reference=resp.headers.get("X-Reference-Id"),
                    message="Deposit request submitted. Awaiting confirmation.",
                    raw=resp.json() if resp.content else {},
                )
            logger.warning("mtn_deposit_failed", status=resp.status_code)
            return PaymentResult(status=PaymentResultStatus.failed, message="Deposit request failed.")
        except httpx.HTTPError as exc:  # pragma: no cover
            logger.error("mtn_deposit_error", error=str(exc))
            return PaymentResult(status=PaymentResultStatus.failed, message="Could not reach MTN.")

    async def verify_payment(self, provider_reference: str) -> PaymentResult:
        if not self.is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="MTN not configured.")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{settings.MTN_BASE_URL}/collection/v1_0/requesttopay/{provider_reference}",
                    headers=await self._headers(),
                )
            data = resp.json() if resp.content else {}
            status = (data.get("status") or "").lower()
            mapping = {
                "successful": PaymentResultStatus.completed,
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
            return PaymentResult(status=PaymentResultStatus.failed, message="MTN not configured.")
        body = {
            "amount": str(ctx.amount),
            "currency": ctx.currency,
            "externalId": ctx.reference,
            "payee": {"partyIdType": "MSISDN", "partyId": (ctx.destination or "").lstrip("0")},
            "payerMessage": "Debate_Settler withdrawal",
            "payeeNote": "Withdrawal",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.MTN_BASE_URL}/disbursement/v1_0/transfer",
                    json=body,
                    headers=await self._headers(),
                )
            if resp.status_code in (200, 201, 202):
                return PaymentResult(
                    status=PaymentResultStatus.pending,
                    provider_reference=resp.headers.get("X-Reference-Id"),
                    message="Withdrawal submitted. Awaiting confirmation.",
                )
            return PaymentResult(status=PaymentResultStatus.failed, message="Withdrawal request failed.")
        except httpx.HTTPError:
            return PaymentResult(status=PaymentResultStatus.failed, message="Could not reach MTN.")

    async def check_payout_status(self, provider_reference: str) -> PaymentResult:
        if not self.is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="MTN not configured.")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{settings.MTN_BASE_URL}/disbursement/v1_0/transfer/{provider_reference}",
                    headers=await self._headers(),
                )
            data = resp.json() if resp.content else {}
            status = (data.get("status") or "").lower()
            mapping = {
                "successful": PaymentResultStatus.completed,
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
        # Verify callback signature/authentication in production before trusting.
        import json

        try:
            data = json.loads(payload.decode())
        except (ValueError, UnicodeDecodeError):
            return PaymentResult(status=PaymentResultStatus.failed, message="Invalid webhook payload.")
        return PaymentResult(
            status=PaymentResultStatus.pending,
            provider_reference=data.get("externalId"),
            message="Webhook received; verifying with provider.",
            raw=data,
        )
