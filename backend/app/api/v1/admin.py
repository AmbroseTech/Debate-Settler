"""Admin endpoints (/api/v1/admin) — permission-controlled (§43).

Sensitive financial actions require moderator/admin role. Admins can submit a
verified settlement result for online debates and manage disputes/users.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.exceptions import NotFoundError
from app.models.base import (
    DebateMode,
    DisputeStatus,
    FinancialState,
    TransactionType,
    UserRole,
    UserStatus,
)
from app.models.debate import Debate, DebateVote
from app.models.notification import AuditLog, Dispute
from app.models.user import User
from app.models.wallet import PaymentTransaction
from app.schemas.common import Message
from app.schemas.misc import AdminStats, SettlementSubmit
from app.services.audit_service import record_audit
from app.settlements import engine

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(UserRole.admin))])


@router.get("/stats", response_model=AdminStats)
async def stats(db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(func.count(User.id)))).scalar_one()
    debates = (await db.execute(select(func.count(Debate.id)))).scalar_one()
    local = (await db.execute(select(func.count(Debate.id)).where(Debate.mode == DebateMode.local))).scalar_one()
    online = (await db.execute(select(func.count(Debate.id)).where(Debate.mode == DebateMode.online))).scalar_one()
    votes = (await db.execute(select(func.count(DebateVote.id)))).scalar_one()
    open_disputes = (
        await db.execute(
            select(func.count(Dispute.id)).where(
                Dispute.status.in_([DisputeStatus.open, DisputeStatus.under_review])
            )
        )
    ).scalar_one()

    async def _sum(type_: TransactionType) -> Decimal:
        value = (
            await db.execute(
                select(func.coalesce(func.sum(PaymentTransaction.amount), 0)).where(
                    PaymentTransaction.type == type_,
                    PaymentTransaction.status == FinancialState.completed,
                )
            )
        ).scalar_one()
        return Decimal(str(value))

    deposits = await _sum(TransactionType.deposit)
    withdrawals = await _sum(TransactionType.withdrawal)
    fees = await _sum(TransactionType.platform_fee)
    return AdminStats(
        users=users, debates=debates, local_debates=local, online_debates=online,
        votes=votes, deposits=deposits, withdrawals=withdrawals, platform_fees=fees,
        open_disputes=open_disputes, currency=settings.DEFAULT_CURRENCY,
    )


@router.get("/users", response_model=List[dict])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(200))
    return [
        {
            "id": str(u.id), "username": u.username, "email": u.email,
            "role": u.role.value, "status": u.status.value,
            "email_verified": u.email_verified, "created_at": u.created_at,
        }
        for u in result.scalars().all()
    ]


@router.post("/users/{user_id}/role", response_model=Message)
async def set_role(user_id: uuid.UUID, role: UserRole, admin: User = Depends(require_role(UserRole.admin)), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    user.role = role
    await record_audit(db, "admin_action", actor_id=admin.id, entity_type="user", entity_id=str(user_id),
                       details={"set_role": role.value})
    await db.commit()
    return Message(message=f"Role updated to {role.value}.")


@router.post("/users/{user_id}/freeze", response_model=Message)
async def freeze_user(user_id: uuid.UUID, admin: User = Depends(require_role(UserRole.admin)), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    user.status = UserStatus.frozen
    from app.models.wallet import Wallet

    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user_id))).scalar_one_or_none()
    if wallet:
        wallet.is_frozen = True
    await record_audit(db, "wallet_freeze", actor_id=admin.id, entity_type="user", entity_id=str(user_id))
    await db.commit()
    return Message(message="User and wallet frozen.")


@router.post("/settlements/submit", response_model=Message)
async def submit_settlement(
    payload: SettlementSubmit,
    admin: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Admin submits a verified result for an online debate (§22)."""
    debate = await db.get(Debate, payload.debate_id)
    if debate is None:
        raise NotFoundError("Debate not found.")
    await engine.settle_debate(
        db, debate, payload.winner_side,
        source_verified=payload.source_verified,
        settlement_source=payload.settlement_source,
        reason=payload.reason,
    )
    await record_audit(db, "settlement", actor_id=admin.id, entity_type="debate", entity_id=str(debate.id),
                       details={"winner_side": payload.winner_side, "source_verified": payload.source_verified})
    await db.commit()
    return Message(message="Settlement recorded.")


@router.get("/audit-logs", response_model=List[dict])
async def audit_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200))
    return [
        {
            "id": str(a.id), "action": a.action, "entity_type": a.entity_type,
            "entity_id": a.entity_id, "actor_id": str(a.actor_id) if a.actor_id else None,
            "details": a.details, "created_at": a.created_at, "entry_hash": a.entry_hash,
        }
        for a in result.scalars().all()
    ]
