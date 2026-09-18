"""Deposits, withdrawals, payment providers and settlement records."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    BaseModel,
    DepositStatus,
    FinancialState,
    WithdrawalStatus,
)


class PaymentProvider(BaseModel):
    """Registered provider configuration (enabled per country/currency)."""

    __tablename__ = "payment_providers"

    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)  # demo|mtn|airtel|stripe|paypal|bank
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)  # mobile_money|card|bank|wallet
    countries: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # comma-separated ISO codes, empty = all
    currencies: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    supports_deposit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_payout: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # non-secret JSON


class Deposit(BaseModel):
    __tablename__ = "deposits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id"), index=True, nullable=False
    )
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    provider_code: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UGX", nullable=False)
    status: Mapped[DepositStatus] = mapped_column(Enum(DepositStatus), default=DepositStatus.initiated, index=True, nullable=False)
    provider_reference: Mapped[Optional[str]] = mapped_column(String(120), index=True, nullable=True)
    destination_hint: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)  # masked phone/account
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(120), unique=True, index=True, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Withdrawal(BaseModel):
    __tablename__ = "withdrawals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id"), index=True, nullable=False
    )
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    provider_code: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UGX", nullable=False)
    status: Mapped[WithdrawalStatus] = mapped_column(Enum(WithdrawalStatus), default=WithdrawalStatus.requested, index=True, nullable=False)
    destination_hint: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    provider_reference: Mapped[Optional[str]] = mapped_column(String(120), index=True, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(120), unique=True, index=True, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class SettlementRecord(BaseModel):
    __tablename__ = "settlement_records"

    debate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debates.id"), unique=True, index=True, nullable=False
    )
    winner_side: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    gross_pool: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    winner_payout: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UGX", nullable=False)
    status: Mapped[FinancialState] = mapped_column(Enum(FinancialState), default=FinancialState.pending, index=True, nullable=False)
    source_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settlement_source: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
