"""MTN Mobile Money adapter (Uganda) (§31).

Production integration must use the official MTN MoMo API with a properly
configured merchant account. Credentials come from environment only. This
adapter never marks a payment complete merely because a request was submitted —
it returns `pending` and relies on `verify_payment`/webhooks for confirmation.
"""
from __future__ import annotations

import re
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
        if not all((settings.MTN_API_KEY, settings.MTN_API_USER, settings.MTN_API_SECRET)):
            return False
        if settings.APP_ENV == "production" and "sandbox" in settings.MTN_BASE_URL.lower():
            return False
        return True

    def _target_environment(self) -> str:
        return "sandbox" if "sandbox" in settings.MTN_BASE_URL.lower() else "mtnuganda"

    @staticmethod
    def _normalize_msisdn(value: str) -> str:
        digits = re.sub(r"\D", "", value or "")
        if digits.startswith("0"):
            digits = "256" + digits[1:]
        elif not digits.startswith("256"):
            digits = "256" + digits
        if not re.fullmatch(r"256\d{9}", digits):
            raise ValueError("Enter a valid Uganda mobile number.")
        return digits

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        response = await client.post(
            f"{settings.MTN_BASE_URL.rstrip('/')}/collection/token/",
            auth=(settings.MTN_API_USER, settings.MTN_API_SECRET),
            headers={"Ocp-Apim-Subscription-Key": settings.MTN_API_KEY},
        )
        response.raise_for_status()
        token = (response.json() or {}).get("access_token")
        if not token:
            raise ValueError("MTN token response did not contain an access token.")
        return token

    async def _headers(self, client: httpx.AsyncClient, reference: str = "") -> Dict[str, str]:
        token = await self._access_token(client)
        return {
            "Ocp-Apim-Subscription-Key": settings.MTN_API_KEY,
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": reference or str(uuid.uuid4()),
            "X-Target-Environment": self._target_environment(),
            "Content-Type": "application/json",
        }

    async def create_deposit(self, ctx: ProviderContext) -> PaymentResult:
        if not self.is_configured():
            return PaymentResult(
                status=PaymentResultStatus.failed,
                message="MTN provider is not configured.",
            )
        try:
            msisdn = self._normalize_msisdn(ctx.destination or "")
        except ValueError as exc:
            return PaymentResult(status=PaymentResultStatus.failed, message=str(exc))
        reference = str(uuid.uuid4())
        body = {
            "amount": str(ctx.amount),
            "currency": ctx.currency,
            "externalId": ctx.reference,
            "payer": {"partyIdType": "MSISDN", "partyId": msisdn},
            "payerMessage": "Debate_Settler deposit",
            "payeeNote": "Deposit",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.MTN_BASE_URL.rstrip('/')}/collection/v1_0/requesttopay",
                    json=body,
                    headers=await self._headers(client, reference),
                )
            if resp.status_code in (200, 201, 202):
                return PaymentResult(
                    status=PaymentResultStatus.pending,
                    provider_reference=reference,
                    message="Deposit request submitted. Awaiting confirmation.",
                    raw=resp.json() if resp.content else {},
                )
            logger.warning("mtn_deposit_failed", status=resp.status_code)
            return PaymentResult(status=PaymentResultStatus.failed, message="Deposit request failed.")
        except (httpx.HTTPError, ValueError) as exc:  # pragma: no cover
            logger.error("mtn_deposit_error", error_type=type(exc).__name__)
            return PaymentResult(status=PaymentResultStatus.failed, message="Could not reach MTN.")

    async def verify_payment(self, provider_reference: str) -> PaymentResult:
        if not self.is_configured():
            return PaymentResult(status=PaymentResultStatus.failed, message="MTN not configured.")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{settings.MTN_BASE_URL.rstrip('/')}/collection/v1_0/requesttopay/{provider_reference}",
                    headers=await self._headers(client),
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
        except (httpx.HTTPError, ValueError):
            return PaymentResult(status=PaymentResultStatus.pending, message="Verification pending.")

    async def create_payout(self, ctx: ProviderContext) -> PaymentResult:
        return PaymentResult(status=PaymentResultStatus.failed, message="MTN withdrawals are unavailable for this Collection-only account.")

    async def check_payout_status(self, provider_reference: str) -> PaymentResult:
        return PaymentResult(status=PaymentResultStatus.failed, provider_reference=provider_reference, message="MTN withdrawals are unavailable for this Collection-only account.")

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
