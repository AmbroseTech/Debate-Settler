"""Wallets, wallet accounts and the double-entry financial ledger.

PostgreSQL is authoritative for money (§37, §62). Amounts use NUMERIC and Python
Decimal — never floats. Every movement produces balanced ledger entries so the
books are always auditable.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, FinancialState, LedgerAccount, TransactionType


class Wallet(BaseModel):
    __tablename__ = "wallets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="UGX", nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Denormalised balances for fast reads; always reconciled against ledger.
    available_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    locked_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    pending_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    accounts: Mapped[List["WalletAccount"]] = relationship(
        back_populates="wallet", cascade="all, delete-orphan"
    )

    @property
    def withdrawable_balance(self) -> Decimal:
        return self.available_balance


class WalletAccount(BaseModel):
    """Sub-accounts of a wallet (available / locked / pending)."""

    __tablename__ = "wallet_accounts"

    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), index=True
    )
    account_type: Mapped[LedgerAccount] = mapped_column(Enum(LedgerAccount, native_enum=False), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    wallet: Mapped["Wallet"] = relationship(back_populates="accounts")


class PaymentTransaction(BaseModel):
    """High-level record of a financial operation (deposit, stake, payout...)."""

    __tablename__ = "payment_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, native_enum=False), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UGX", nullable=False)
    status: Mapped[FinancialState] = mapped_column(Enum(FinancialState, native_enum=False), nullable=False, index=True)
    provider: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    provider_reference: Mapped[Optional[str]] = mapped_column(String(120), index=True, nullable=True)
    debate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debates.id"), nullable=True, index=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(120), unique=True, index=True, nullable=True)
    metadata_: Mapped[Optional[str]] = mapped_column("metadata", Text, nullable=True)


class LedgerEntry(BaseModel):
    """Single leg of a double-entry ledger record."""

    __tablename__ = "ledger_entries"

    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_transactions.id"), index=True, nullable=True
    )
    wallet_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id"), index=True, nullable=True
    )
    account: Mapped[LedgerAccount] = mapped_column(Enum(LedgerAccount, native_enum=False), nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(String(10), nullable=False)  # debit | credit
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UGX", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    debate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debates.id"), nullable=True
    )
