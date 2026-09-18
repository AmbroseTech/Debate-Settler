"""Payment provider abstraction.

Business logic never depends on a single provider. Each adapter implements the
same interface, so a demo integration can be swapped for a real approved
provider without touching the rest of the app (§33, §100).

Secrets come only from environment/config — never hard-coded (§70).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class PaymentResultStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


@dataclass
class PaymentResult:
    status: PaymentResultStatus
    provider_reference: Optional[str] = None
    message: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderContext:
    amount: Any  # Decimal
    currency: str
    destination: Optional[str] = None
    reference: Optional[str] = None
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PaymentProviderAdapter(abc.ABC):
    code: str = "base"
    display_name: str = "Base Provider"
    kind: str = "generic"
    is_demo: bool = False
    supports_deposit: bool = True
    supports_payout: bool = False

    @abc.abstractmethod
    async def create_deposit(self, ctx: ProviderContext) -> PaymentResult: ...

    @abc.abstractmethod
    async def verify_payment(self, provider_reference: str) -> PaymentResult: ...

    @abc.abstractmethod
    async def create_payout(self, ctx: ProviderContext) -> PaymentResult: ...

    @abc.abstractmethod
    async def check_payout_status(self, provider_reference: str) -> PaymentResult: ...

    @abc.abstractmethod
    async def handle_webhook(self, payload: bytes, headers: Dict[str, str]) -> PaymentResult: ...

    async def refund(self, provider_reference: str, ctx: ProviderContext) -> PaymentResult:
        return PaymentResult(
            status=PaymentResultStatus.failed,
            message="Refunds are not supported by this provider.",
        )

    def countries(self) -> Optional[list[str]]:
        return None
