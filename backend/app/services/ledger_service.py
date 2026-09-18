"""Wallet & double-entry ledger service.

Postgres is authoritative for money. Every balance movement writes balanced
ledger entries and updates the wallet's denormalised balances inside the same
DB transaction, using row locking (`SELECT ... FOR UPDATE`) to prevent races
(§61). Amounts are always Decimal.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    InsufficientFundsError,
    NotFoundError,
)
from app.core.money import ZERO, quantize, to_decimal
from app.core.security import generate_reference
from app.models.base import FinancialState, LedgerAccount, TransactionType
from app.models.wallet import LedgerEntry, PaymentTransaction, Wallet, WalletAccount


async def get_or_create_wallet(db: AsyncSession, user_id: uuid.UUID, currency: str = "UGX") -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = result.scalar_one_or_none()
    if wallet is None:
        wallet = Wallet(user_id=user_id, currency=currency)
        db.add(wallet)
        await db.flush()
        for account_type in (
            LedgerAccount.user_available,
            LedgerAccount.user_locked,
            LedgerAccount.user_pending,
        ):
            db.add(WalletAccount(wallet_id=wallet.id, account_type=account_type, balance=ZERO))
        await db.flush()
    return wallet


async def lock_wallet(db: AsyncSession, wallet_id: uuid.UUID) -> Wallet:
    """Acquire a row lock on the wallet for the duration of the transaction."""
    result = await db.execute(
        select(Wallet).where(Wallet.id == wallet_id).with_for_update()
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise NotFoundError("Wallet not found.")
    return wallet


def _create_transaction(
    *,
    user_id: uuid.UUID,
    type_: TransactionType,
    amount: Decimal,
    currency: str,
    status: FinancialState,
    provider: Optional[str] = None,
    provider_reference: Optional[str] = None,
    debate_id: Optional[uuid.UUID] = None,
    is_demo: bool = False,
    idempotency_key: Optional[str] = None,
    reference_prefix: str = "DS-TX",
) -> PaymentTransaction:
    return PaymentTransaction(
        user_id=user_id,
        reference=generate_reference(reference_prefix),
        type=type_,
        amount=quantize(amount),
        currency=currency,
        status=status,
        provider=provider,
        provider_reference=provider_reference,
        debate_id=debate_id,
        is_demo=is_demo,
        idempotency_key=idempotency_key,
    )


def _ledger_entry(
    *,
    transaction_id: uuid.UUID,
    wallet_id: Optional[uuid.UUID],
    account: LedgerAccount,
    entry_type: str,
    amount: Decimal,
    currency: str,
    description: str,
    debate_id: Optional[uuid.UUID] = None,
) -> LedgerEntry:
    return LedgerEntry(
        transaction_id=transaction_id,
        wallet_id=wallet_id,
        account=account,
        entry_type=entry_type,
        amount=quantize(amount),
        currency=currency,
        description=description,
        debate_id=debate_id,
    )


async def credit_available(
    db: AsyncSession,
    wallet: Wallet,
    amount: Decimal,
    *,
    type_: TransactionType = TransactionType.deposit,
    description: str = "Deposit",
    provider: Optional[str] = None,
    provider_reference: Optional[str] = None,
    is_demo: bool = False,
    idempotency_key: Optional[str] = None,
) -> PaymentTransaction:
    """Add funds to a user's available balance (e.g. completed deposit)."""
    amount = to_decimal(amount)
    if amount <= 0:
        raise ConflictError("Amount must be positive.")
    wallet = await lock_wallet(db, wallet.id)
    if wallet.is_frozen:
        raise ConflictError("This wallet is frozen. Please contact support.")

    tx = _create_transaction(
        user_id=wallet.user_id,
        type_=type_,
        amount=amount,
        currency=wallet.currency,
        status=FinancialState.completed,
        provider=provider,
        provider_reference=provider_reference,
        is_demo=is_demo,
        idempotency_key=idempotency_key,
        reference_prefix="DS-DEP" if type_ == TransactionType.deposit else "DS-TX",
    )
    db.add(tx)
    await db.flush()

    wallet.available_balance = quantize(wallet.available_balance + amount)
    db.add(
        _ledger_entry(
            transaction_id=tx.id,
            wallet_id=wallet.id,
            account=LedgerAccount.user_available,
            entry_type="credit",
            amount=amount,
            currency=wallet.currency,
            description=description,
        )
    )
    await db.flush()
    return tx


async def lock_stake(
    db: AsyncSession,
    wallet: Wallet,
    amount: Decimal,
    *,
    debate_id: uuid.UUID,
    description: str = "Debate stake locked",
    idempotency_key: Optional[str] = None,
) -> PaymentTransaction:
    """Move funds from available -> locked for an active debate stake."""
    amount = to_decimal(amount)
    wallet = await lock_wallet(db, wallet.id)
    if wallet.is_frozen:
        raise ConflictError("This wallet is frozen. Please contact support.")
    if wallet.available_balance < amount:
        raise InsufficientFundsError()

    tx = _create_transaction(
        user_id=wallet.user_id,
        type_=TransactionType.stake_lock,
        amount=amount,
        currency=wallet.currency,
        status=FinancialState.locked,
        debate_id=debate_id,
        idempotency_key=idempotency_key,
        reference_prefix="DS-STK",
    )
    db.add(tx)
    await db.flush()

    wallet.available_balance = quantize(wallet.available_balance - amount)
    wallet.locked_balance = quantize(wallet.locked_balance + amount)
    db.add(
        _ledger_entry(
            transaction_id=tx.id, wallet_id=wallet.id, account=LedgerAccount.user_available,
            entry_type="debit", amount=amount, currency=wallet.currency,
            description=description, debate_id=debate_id,
        )
    )
    db.add(
        _ledger_entry(
            transaction_id=tx.id, wallet_id=wallet.id, account=LedgerAccount.user_locked,
            entry_type="credit", amount=amount, currency=wallet.currency,
            description=description, debate_id=debate_id,
        )
    )
    await db.flush()
    return tx


async def release_stake(
    db: AsyncSession,
    wallet: Wallet,
    amount: Decimal,
    *,
    debate_id: uuid.UUID,
    description: str = "Stake released",
) -> PaymentTransaction:
    """Return locked funds to available (cancellation / draw refund)."""
    amount = to_decimal(amount)
    wallet = await lock_wallet(db, wallet.id)
    if wallet.locked_balance < amount:
        raise ConflictError("Locked balance is insufficient for this release.")

    tx = _create_transaction(
        user_id=wallet.user_id,
        type_=TransactionType.refund,
        amount=amount,
        currency=wallet.currency,
        status=FinancialState.refunded,
        debate_id=debate_id,
        reference_prefix="DS-RFD",
    )
    db.add(tx)
    await db.flush()

    wallet.locked_balance = quantize(wallet.locked_balance - amount)
    wallet.available_balance = quantize(wallet.available_balance + amount)
    db.add(
        _ledger_entry(
            transaction_id=tx.id, wallet_id=wallet.id, account=LedgerAccount.user_locked,
            entry_type="debit", amount=amount, currency=wallet.currency,
            description=description, debate_id=debate_id,
        )
    )
    db.add(
        _ledger_entry(
            transaction_id=tx.id, wallet_id=wallet.id, account=LedgerAccount.user_available,
            entry_type="credit", amount=amount, currency=wallet.currency,
            description=description, debate_id=debate_id,
        )
    )
    await db.flush()
    return tx


async def settle_stake_to_winner(
    db: AsyncSession,
    *,
    loser_wallet: Wallet,
    winner_wallet: Wallet,
    stake_amount: Decimal,
    platform_fee_amount: Decimal,
    debate_id: uuid.UUID,
    is_demo: bool = False,
) -> Tuple[PaymentTransaction, PaymentTransaction]:
    """Move loser's locked stake to the winner net of the platform fee.

    Produces: (1) a payout crediting the winner, (2) a platform-fee record.
    The loser's locked balance is reduced by their full stake.
    """
    stake_amount = to_decimal(stake_amount)
    platform_fee_amount = to_decimal(platform_fee_amount)
    net_payout = quantize(stake_amount - platform_fee_amount)

    loser = await lock_wallet(db, loser_wallet.id)
    winner = await lock_wallet(db, winner_wallet.id)

    if loser.locked_balance < stake_amount:
        raise ConflictError("Loser locked balance is insufficient for settlement.")

    # Payout to winner (their own locked stake is released separately).
    payout_tx = _create_transaction(
        user_id=winner.user_id,
        type_=TransactionType.payout,
        amount=net_payout,
        currency=winner.currency,
        status=FinancialState.completed,
        debate_id=debate_id,
        is_demo=is_demo,
        reference_prefix="DS-PAY",
    )
    db.add(payout_tx)
    await db.flush()

    loser.locked_balance = quantize(loser.locked_balance - stake_amount)
    winner.available_balance = quantize(winner.available_balance + net_payout)

    db.add(
        _ledger_entry(
            transaction_id=payout_tx.id, wallet_id=loser.id, account=LedgerAccount.user_locked,
            entry_type="debit", amount=stake_amount, currency=loser.currency,
            description="Losing stake", debate_id=debate_id,
        )
    )
    db.add(
        _ledger_entry(
            transaction_id=payout_tx.id, wallet_id=winner.id, account=LedgerAccount.user_available,
            entry_type="credit", amount=net_payout, currency=winner.currency,
            description="Winner settlement (net of fee)", debate_id=debate_id,
        )
    )

    # Platform fee record.
    fee_tx = _create_transaction(
        user_id=winner.user_id,
        type_=TransactionType.platform_fee,
        amount=platform_fee_amount,
        currency=winner.currency,
        status=FinancialState.completed,
        debate_id=debate_id,
        is_demo=is_demo,
        reference_prefix="DS-FEE",
    )
    db.add(fee_tx)
    await db.flush()
    db.add(
        _ledger_entry(
            transaction_id=fee_tx.id, wallet_id=None, account=LedgerAccount.platform_fee_revenue,
            entry_type="credit", amount=platform_fee_amount, currency=winner.currency,
            description="Platform settlement fee", debate_id=debate_id,
        )
    )
    await db.flush()
    return payout_tx, fee_tx


async def debit_available(
    db: AsyncSession,
    wallet: Wallet,
    amount: Decimal,
    *,
    type_: TransactionType = TransactionType.withdrawal,
    description: str = "Withdrawal",
    provider: Optional[str] = None,
    status: FinancialState = FinancialState.processing,
    idempotency_key: Optional[str] = None,
) -> PaymentTransaction:
    """Reserve funds from available balance (e.g. withdrawal request)."""
    amount = to_decimal(amount)
    wallet = await lock_wallet(db, wallet.id)
    if wallet.is_frozen:
        raise ConflictError("This wallet is frozen. Please contact support.")
    if wallet.available_balance < amount:
        raise InsufficientFundsError()

    tx = _create_transaction(
        user_id=wallet.user_id,
        type_=type_,
        amount=amount,
        currency=wallet.currency,
        status=status,
        provider=provider,
        idempotency_key=idempotency_key,
        reference_prefix="DS-WD",
    )
    db.add(tx)
    await db.flush()

    wallet.available_balance = quantize(wallet.available_balance - amount)
    wallet.pending_balance = quantize(wallet.pending_balance + amount)
    db.add(
        _ledger_entry(
            transaction_id=tx.id, wallet_id=wallet.id, account=LedgerAccount.user_available,
            entry_type="debit", amount=amount, currency=wallet.currency, description=description,
        )
    )
    db.add(
        _ledger_entry(
            transaction_id=tx.id, wallet_id=wallet.id, account=LedgerAccount.user_pending,
            entry_type="credit", amount=amount, currency=wallet.currency, description=description,
        )
    )
    await db.flush()
    return tx


async def complete_pending(
    db: AsyncSession,
    wallet: Wallet,
    amount: Decimal,
    *,
    description: str = "Withdrawal completed",
) -> None:
    """Funds leave the platform: pending balance decreases (money paid out)."""
    amount = to_decimal(amount)
    wallet = await lock_wallet(db, wallet.id)
    if wallet.pending_balance < amount:
        raise ConflictError("Pending balance is insufficient to complete.")
    wallet.pending_balance = quantize(wallet.pending_balance - amount)
    db.add(
        _ledger_entry(
            transaction_id=None, wallet_id=wallet.id, account=LedgerAccount.user_pending,
            entry_type="debit", amount=amount, currency=wallet.currency, description=description,
        )
    )
    await db.flush()


async def reverse_pending_to_available(
    db: AsyncSession,
    wallet: Wallet,
    amount: Decimal,
    *,
    description: str = "Withdrawal failed — funds returned",
) -> None:
    """Return pending funds to available (failed/cancelled withdrawal)."""
    amount = to_decimal(amount)
    wallet = await lock_wallet(db, wallet.id)
    if wallet.pending_balance < amount:
        raise ConflictError("Pending balance is insufficient to reverse.")
    wallet.pending_balance = quantize(wallet.pending_balance - amount)
    wallet.available_balance = quantize(wallet.available_balance + amount)
    db.add(
        _ledger_entry(
            transaction_id=None, wallet_id=wallet.id, account=LedgerAccount.user_pending,
            entry_type="debit", amount=amount, currency=wallet.currency, description=description,
        )
    )
    db.add(
        _ledger_entry(
            transaction_id=None, wallet_id=wallet.id, account=LedgerAccount.user_available,
            entry_type="credit", amount=amount, currency=wallet.currency, description=description,
        )
    )
    await db.flush()


async def list_transactions(
    db: AsyncSession, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0,
    type_: Optional[TransactionType] = None,
) -> Tuple[List[PaymentTransaction], int]:
    from sqlalchemy import func

    query = select(PaymentTransaction).where(PaymentTransaction.user_id == user_id)
    if type_ is not None:
        query = query.where(PaymentTransaction.type == type_)
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(PaymentTransaction.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total
