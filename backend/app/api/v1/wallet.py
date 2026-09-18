"""Wallet endpoints (/api/v1/wallet, /deposits, /withdrawals, /payments)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.models.base import TransactionType
from app.models.payment import Deposit, Withdrawal
from app.models.user import User
from app.schemas.common import Message, Paginated
from app.schemas.wallet import (
    DepositOut,
    DepositRequest,
    ProviderOption,
    StakePreview,
    TransactionOut,
    WalletOut,
    WithdrawalOut,
    WithdrawalQuote,
    WithdrawalRequest,
)
from app.services import ledger_service, wallet_service

router = APIRouter(tags=["wallet"])


@router.get("/wallet", response_model=WalletOut)
async def get_wallet(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    wallet = await wallet_service.get_wallet(db, user.id)
    await db.commit()
    return WalletOut(
        id=wallet.id,
        currency=wallet.currency,
        is_frozen=wallet.is_frozen,
        available_balance=wallet.available_balance,
        locked_balance=wallet.locked_balance,
        pending_balance=wallet.pending_balance,
        withdrawable_balance=wallet.withdrawable_balance,
    )


@router.get("/wallet/transactions", response_model=Paginated[TransactionOut])
async def transactions(
    type: Optional[TransactionType] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    txs, total = await ledger_service.list_transactions(
        db, user.id, limit=page_size, offset=(page - 1) * page_size, type_=type
    )
    return Paginated.create([TransactionOut.model_validate(t) for t in txs], total, page, page_size)


@router.get("/wallet/stake-preview", response_model=StakePreview)
async def stake_preview(amount: Decimal = Query(..., gt=0)):
    return StakePreview(**wallet_service.stake_preview(amount, "UGX"))


@router.get("/payments/providers", response_model=List[ProviderOption])
async def providers(
    for_payout: bool = False,
    user: User = Depends(get_current_user),
):
    options = await wallet_service.list_providers(user, for_payout=for_payout)
    return [ProviderOption(**o) for o in options]


# --- Deposits ---

@router.post("/deposits", response_model=DepositOut, status_code=201)
async def create_deposit(
    payload: DepositRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deposit = await wallet_service.create_deposit(
        db, user, payload.provider_code, payload.amount,
        payload.destination, payload.idempotency_key,
    )
    await db.commit()
    await db.refresh(deposit)
    msg = (
        "DEMO FUNDS — simulated deposit."
        if deposit.is_demo
        else "Your deposit is being confirmed."
    )
    return DepositOut(**{**DepositOut.model_validate(deposit).model_dump(), "message": msg})


@router.post("/deposits/{deposit_id}/verify", response_model=DepositOut)
async def verify_deposit(
    deposit_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deposit = await wallet_service.verify_deposit(db, deposit_id)
    await db.commit()
    return DepositOut(**{**DepositOut.model_validate(deposit).model_dump(), "message": ""})


@router.get("/deposits", response_model=List[DepositOut])
async def list_deposits(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Deposit).where(Deposit.user_id == user.id).order_by(Deposit.created_at.desc()).limit(50)
    )
    return [
        DepositOut(**{**DepositOut.model_validate(d).model_dump(), "message": ""})
        for d in result.scalars().all()
    ]


# --- Withdrawals ---

@router.get("/withdrawals/quote", response_model=WithdrawalQuote)
async def withdrawal_quote(amount: Decimal = Query(..., gt=0)):
    return WithdrawalQuote(**await wallet_service.quote_withdrawal(amount, "UGX"))


@router.post("/withdrawals", response_model=WithdrawalOut, status_code=201)
async def create_withdrawal(
    payload: WithdrawalRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    withdrawal = await wallet_service.create_withdrawal(
        db, user, payload.provider_code, payload.amount, payload.destination, payload.idempotency_key
    )
    await db.commit()
    await db.refresh(withdrawal)
    return WithdrawalOut.model_validate(withdrawal)


@router.get("/withdrawals", response_model=List[WithdrawalOut])
async def list_withdrawals(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Withdrawal).where(Withdrawal.user_id == user.id).order_by(Withdrawal.created_at.desc()).limit(50)
    )
    return [WithdrawalOut.model_validate(w) for w in result.scalars().all()]


@router.post("/withdrawals/{withdrawal_id}/status", response_model=WithdrawalOut)
async def check_withdrawal(
    withdrawal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    withdrawal = await wallet_service.check_withdrawal_status(db, withdrawal_id)
    await db.commit()
    return WithdrawalOut.model_validate(withdrawal)


# --- Webhooks (signature verified inside provider adapters) ---

@router.post("/payments/webhook/{provider_code}")
async def payment_webhook(provider_code: str, request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    headers = dict(request.headers)
    await wallet_service.handle_deposit_webhook(db, provider_code, payload, headers)
    await db.commit()
    return Message(message="Webhook received.")
