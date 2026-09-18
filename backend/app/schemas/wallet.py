"""Wallet, transaction, deposit and withdrawal schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import DepositStatus, FinancialState, TransactionType, WithdrawalStatus


class WalletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    currency: str
    is_frozen: bool
    available_balance: Decimal
    locked_balance: Decimal
    pending_balance: Decimal
    withdrawable_balance: Decimal


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    type: TransactionType
    amount: Decimal
    currency: str
    status: FinancialState
    provider: Optional[str] = None
    debate_id: Optional[uuid.UUID] = None
    is_demo: bool = False
    created_at: datetime


class ProviderOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    display_name: str
    kind: str
    supports_deposit: bool
    supports_payout: bool
    is_demo: bool


class DepositRequest(BaseModel):
    provider_code: str
    amount: Decimal = Field(..., gt=0)
    destination: Optional[str] = Field(None, description="e.g. mobile money number")
    idempotency_key: Optional[str] = None


class DepositOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    provider_code: str
    amount: Decimal
    currency: str
    status: DepositStatus
    is_demo: bool
    provider_reference: Optional[str] = None
    message: str = ""
    created_at: datetime


class WithdrawalRequest(BaseModel):
    provider_code: str
    amount: Decimal = Field(..., gt=0)
    destination: str = Field(..., description="Mobile number / bank account")
    pin: Optional[str] = Field(None, description="Wallet PIN / 2FA code")
    idempotency_key: Optional[str] = None


class WithdrawalQuote(BaseModel):
    amount: Decimal
    fee: Decimal
    net_amount: Decimal
    currency: str
    estimated_processing: str


class WithdrawalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    provider_code: str
    amount: Decimal
    fee: Decimal
    net_amount: Decimal
    currency: str
    status: WithdrawalStatus
    is_demo: bool
    destination_hint: Optional[str] = None
    created_at: datetime


class StakePreview(BaseModel):
    """Financial transparency shown before a user commits (§24, §59)."""

    your_stake: Decimal
    total_pool: Decimal
    platform_fee_percent: Decimal
    platform_fee_amount: Decimal
    estimated_winner_settlement: Decimal
    currency: str
    is_demo: bool
    real_money_enabled: bool
