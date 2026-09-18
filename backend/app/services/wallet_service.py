"""Wallet service: deposits, withdrawals, stake preview (§24-§36).

Orchestrates provider calls + ledger movements. Idempotency keys and provider
references prevent double-crediting (§40). Never marks a payment complete just
because a request was submitted.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    FeatureDisabledError,
    NotFoundError,
    ValidationError,
)
from app.core.money import calculate_fee, quantize, to_decimal
from app.core.security import generate_reference
from app.models.base import DepositStatus, FinancialState, TransactionType, WithdrawalStatus
from app.models.payment import Deposit, Withdrawal
from app.models.user import User
from app.models.wallet import Wallet
from app.payments.base import PaymentResultStatus, ProviderContext
from app.payments.registry import real_money_enabled, resolve_provider
from app.services import ledger_service, notification_service
from app.services.audit_service import record_audit


def _mask_destination(destination: Optional[str]) -> Optional[str]:
    if not destination:
        return None
    if len(destination) <= 4:
        return "*" * len(destination)
    return f"{destination[:2]}{'*' * (len(destination) - 4)}{destination[-2:]}"


async def get_wallet(db: AsyncSession, user_id: uuid.UUID) -> Wallet:
    return await ledger_service.get_or_create_wallet(db, user_id, settings.DEFAULT_CURRENCY)


def stake_preview(stake: Decimal, currency: str) -> dict:
    """Transparent breakdown shown before a user commits (§59)."""
    stake = to_decimal(stake)
    total_pool = quantize(stake * 2)
    fee_fraction = settings.platform_fee_fraction
    fee_amount = calculate_fee(total_pool, fee_fraction)
    winner_settlement = quantize(total_pool - fee_amount)
    return {
        "your_stake": stake,
        "total_pool": total_pool,
        "platform_fee_percent": settings.PLATFORM_FEE_PERCENT,
        "platform_fee_amount": fee_amount,
        "estimated_winner_settlement": winner_settlement,
        "currency": currency,
        "is_demo": not real_money_enabled(),
        "real_money_enabled": real_money_enabled(),
    }


# --- Deposits ---

async def create_deposit(
    db: AsyncSession,
    user: User,
    provider_code: str,
    amount: Decimal,
    destination: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Deposit:
    amount = to_decimal(amount)
    if amount <= 0:
        raise ValidationError("Enter an amount greater than zero.")

    # Idempotency: return the existing deposit for this key.
    if idempotency_key:
        existing = await db.execute(
            select(Deposit).where(Deposit.idempotency_key == idempotency_key)
        )
        found = existing.scalar_one_or_none()
        if found:
            return found

    provider = resolve_provider(provider_code, user.country_code)
    if provider is None or not provider.supports_deposit:
        raise FeatureDisabledError("That payment method isn't available for your account or region.")
    if provider.is_demo is False and not settings.ENABLE_LOCAL_MONEY:
        raise FeatureDisabledError("Real-money deposits are not enabled in this configuration.")

    wallet = await get_wallet(db, user.id)
    if wallet.is_frozen:
        raise ConflictError("Your wallet is frozen. Please contact support.")

    deposit = Deposit(
        user_id=user.id,
        wallet_id=wallet.id,
        reference=generate_reference("DS-DEP"),
        provider_code=provider.code,
        amount=amount,
        currency=wallet.currency,
        status=DepositStatus.initiated,
        destination_hint=_mask_destination(destination),
        is_demo=provider.is_demo,
        idempotency_key=idempotency_key,
    )
    db.add(deposit)
    await db.flush()

    ctx = ProviderContext(
        amount=amount, currency=wallet.currency, destination=destination,
        reference=deposit.reference, idempotency_key=idempotency_key,
    )
    result = await provider.create_deposit(ctx)
    deposit.provider_reference = result.provider_reference
    deposit.status = _map_deposit_status(result.status)
    await record_audit(
        db, "payment_initiated", actor_id=user.id, entity_type="deposit",
        entity_id=str(deposit.id),
        details={"provider": provider.code, "amount": str(amount), "demo": provider.is_demo},
    )
    await db.flush()

    # Demo deposits complete immediately for a smooth dev experience; live
    # deposits stay pending until verified via webhook/verify.
    if provider.is_demo and deposit.status == DepositStatus.completed:
        await _complete_deposit(db, deposit, user, notify=False)
    return deposit


def _map_deposit_status(status: PaymentResultStatus) -> DepositStatus:
    return {
        PaymentResultStatus.completed: DepositStatus.completed,
        PaymentResultStatus.pending: DepositStatus.pending,
        PaymentResultStatus.failed: DepositStatus.failed,
    }[status]


async def _complete_deposit(db: AsyncSession, deposit: Deposit, user: Optional[User] = None, notify: bool = True) -> None:
    # Idempotency guard: completed_at is only set once the wallet has actually
    # been credited, so re-entry (webhook + verify) never double-credits. The
    # ledger also dedups on idempotency_key as a second line of defence.
    if deposit.completed_at is not None:
        return
    wallet = await ledger_service.lock_wallet(db, deposit.wallet_id)
    deposit.status = DepositStatus.completed
    deposit.completed_at = datetime.now(timezone.utc)
    await ledger_service.credit_available(
        db, wallet, deposit.amount,
        type_=TransactionType.deposit,
        description=f"Deposit via {deposit.provider_code}",
        provider=deposit.provider_code,
        provider_reference=deposit.provider_reference,
        is_demo=deposit.is_demo,
        idempotency_key=f"deposit:{deposit.id}",
    )
    await record_audit(
        db, "payment_confirmed", entity_type="deposit", entity_id=str(deposit.id),
        details={"amount": str(deposit.amount), "demo": deposit.is_demo},
    )
    if notify and user is not None:
        await notification_service.notify(
            db, user.id, "Deposit received",
            ("DEMO FUNDS — " if deposit.is_demo else "")
            + f"{deposit.currency} {deposit.amount} added to your wallet.",
            category="wallet",
        )


async def verify_deposit(db: AsyncSession, deposit_id: uuid.UUID) -> Deposit:
    deposit = await db.get(Deposit, deposit_id)
    if deposit is None:
        raise NotFoundError("Deposit not found.")
    if deposit.status == DepositStatus.completed:
        return deposit
    provider = resolve_provider(deposit.provider_code)
    if provider is None or not deposit.provider_reference:
        return deposit
    result = await provider.verify_payment(deposit.provider_reference)
    if result.status == PaymentResultStatus.completed:
        await _complete_deposit(db, deposit)
    elif result.status == PaymentResultStatus.failed:
        deposit.status = DepositStatus.failed
    await db.flush()
    return deposit


async def handle_deposit_webhook(
    db: AsyncSession, provider_code: str, payload: bytes, headers: dict
) -> None:
    """Idempotent webhook handling (§40). Duplicate webhooks never double-credit."""
    provider = resolve_provider(provider_code)
    if provider is None:
        raise NotFoundError("Unknown provider.")
    result = await provider.handle_webhook(payload, headers)
    if not result.provider_reference:
        return
    existing = await db.execute(
        select(Deposit).where(Deposit.provider_reference == result.provider_reference)
    )
    deposit = existing.scalar_one_or_none()
    if deposit is None or deposit.status == DepositStatus.completed:
        return
    if result.status == PaymentResultStatus.completed:
        await _complete_deposit(db, deposit)
    await db.flush()


# --- Withdrawals ---

async def quote_withdrawal(amount: Decimal, currency: str) -> dict:
    amount = to_decimal(amount)
    fee = calculate_fee(amount, settings.WITHDRAWAL_FEE_PERCENT / Decimal(100))
    net = quantize(amount - fee)
    return {
        "amount": amount,
        "fee": fee,
        "net_amount": net,
        "currency": currency,
        "estimated_processing": "Shown by your provider after confirmation.",
    }


async def create_withdrawal(
    db: AsyncSession,
    user: User,
    provider_code: str,
    amount: Decimal,
    destination: str,
    idempotency_key: Optional[str] = None,
) -> Withdrawal:
    if not settings.ENABLE_WITHDRAWALS and real_money_enabled():
        raise FeatureDisabledError("Withdrawals are not enabled in this configuration.")
    amount = to_decimal(amount)
    if amount <= 0:
        raise ValidationError("Enter an amount greater than zero.")

    if idempotency_key:
        existing = await db.execute(
            select(Withdrawal).where(Withdrawal.idempotency_key == idempotency_key)
        )
        found = existing.scalar_one_or_none()
        if found:
            return found

    provider = resolve_provider(provider_code, user.country_code, for_payout=True)
    if provider is None or not provider.supports_payout:
        raise FeatureDisabledError("That withdrawal method isn't available for your account or region.")

    wallet = await get_wallet(db, user.id)
    if wallet.is_frozen:
        raise ConflictError("Your wallet is frozen. Please contact support.")

    quote = await quote_withdrawal(amount, wallet.currency)
    fee = quote["fee"]
    net = quote["net_amount"]

    withdrawal = Withdrawal(
        user_id=user.id,
        wallet_id=wallet.id,
        reference=generate_reference("DS-WD"),
        provider_code=provider.code,
        amount=amount,
        fee=fee,
        net_amount=net,
        currency=wallet.currency,
        status=WithdrawalStatus.requested,
        destination_hint=_mask_destination(destination),
        is_demo=provider.is_demo,
        idempotency_key=idempotency_key,
    )
    db.add(withdrawal)
    await db.flush()

    # Reserve the full amount (amount incl. fee) from available balance.
    await ledger_service.debit_available(
        db, wallet, amount,
        type_=TransactionType.withdrawal,
        description=f"Withdrawal to {provider.code}",
        provider=provider.code,
        status=FinancialState.processing,
        idempotency_key=f"withdrawal:{withdrawal.id}",
    )

    ctx = ProviderContext(
        amount=net, currency=wallet.currency, destination=destination,
        reference=withdrawal.reference, idempotency_key=idempotency_key,
    )
    result = await provider.create_payout(ctx)
    withdrawal.provider_reference = result.provider_reference
    if result.status == PaymentResultStatus.failed:
        withdrawal.status = WithdrawalStatus.failed
        await ledger_service.reverse_pending_to_available(
            db, wallet, amount, description="Withdrawal failed — funds returned"
        )
    elif result.status == PaymentResultStatus.completed:
        withdrawal.status = WithdrawalStatus.completed
        withdrawal.completed_at = datetime.now(timezone.utc)
        await ledger_service.complete_pending(db, wallet, amount)
    else:
        withdrawal.status = WithdrawalStatus.processing

    await record_audit(
        db, "withdrawal_request", actor_id=user.id, entity_type="withdrawal",
        entity_id=str(withdrawal.id),
        details={"provider": provider.code, "amount": str(amount), "status": withdrawal.status.value},
    )
    await notification_service.notify_withdrawal_status(
        db, user.id, withdrawal.status.value, withdrawal.reference
    )
    await db.flush()
    return withdrawal


async def check_withdrawal_status(db: AsyncSession, withdrawal_id: uuid.UUID) -> Withdrawal:
    withdrawal = await db.get(Withdrawal, withdrawal_id)
    if withdrawal is None:
        raise NotFoundError("Withdrawal not found.")
    if withdrawal.status in (WithdrawalStatus.completed, WithdrawalStatus.failed):
        return withdrawal
    provider = resolve_provider(withdrawal.provider_code)
    if provider is None or not withdrawal.provider_reference:
        return withdrawal
    result = await provider.check_payout_status(withdrawal.provider_reference)
    wallet = await ledger_service.lock_wallet(db, withdrawal.wallet_id)
    if result.status == PaymentResultStatus.completed:
        withdrawal.status = WithdrawalStatus.completed
        withdrawal.completed_at = datetime.now(timezone.utc)
        await ledger_service.complete_pending(db, wallet, withdrawal.amount)
    elif result.status == PaymentResultStatus.failed:
        withdrawal.status = WithdrawalStatus.failed
        await ledger_service.reverse_pending_to_available(db, wallet, withdrawal.amount)
    await record_audit(
        db, "withdrawal_status_change", entity_type="withdrawal",
        entity_id=str(withdrawal.id), details={"status": withdrawal.status.value},
    )
    await db.flush()
    return withdrawal


async def list_providers(user: User, for_payout: bool = False) -> List[dict]:
    from app.payments.registry import available_providers

    providers = available_providers(user.country_code, for_payout=for_payout)
    return [
        {
            "code": p.code,
            "display_name": p.display_name,
            "kind": p.kind,
            "supports_deposit": p.supports_deposit,
            "supports_payout": p.supports_payout,
            "is_demo": p.is_demo,
        }
        for p in providers
    ]
