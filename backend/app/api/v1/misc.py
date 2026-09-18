"""Categories, notifications, disputes and games endpoints."""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import NotFoundError
from app.models.base import DisputeStatus, GameStatus, GameType, NotificationChannel, UserRole
from app.models.category import Category
from app.models.debate import Debate
from app.models.notification import Dispute, Game, Notification
from app.models.user import User
from app.schemas.common import Message
from app.schemas.misc import (
    CategoryOut,
    DisputeCreate,
    DisputeOut,
    DisputeResolve,
    GameCreate,
    GameOut,
    NotificationOut,
)
from app.services import notification_service
from app.services.audit_service import record_audit

categories_router = APIRouter(prefix="/categories", tags=["categories"])
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])
disputes_router = APIRouter(prefix="/disputes", tags=["disputes"])
games_router = APIRouter(prefix="/games", tags=["games"])


# --- Categories ---

@categories_router.get("", response_model=List[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order))
    return [CategoryOut.model_validate(c) for c in result.scalars().all()]


# --- Notifications ---

@notifications_router.get("", response_model=List[NotificationOut])
async def list_notifications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(100)
    )
    return [NotificationOut.model_validate(n) for n in result.scalars().all()]


@notifications_router.post("/{notification_id}/read", response_model=Message)
async def mark_read(notification_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    n = await db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise NotFoundError("Notification not found.")
    n.read = True
    await db.commit()
    return Message(message="Marked as read.")


@notifications_router.post("/read-all", response_model=Message)
async def mark_all_read(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.user_id == user.id, Notification.read.is_(False)))
    for n in result.scalars().all():
        n.read = True
    await db.commit()
    return Message(message="All notifications marked as read.")


# --- Disputes (§23) ---

@disputes_router.post("", response_model=DisputeOut, status_code=201)
async def create_dispute(payload: DisputeCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    debate = await db.get(Debate, payload.debate_id)
    if debate is None:
        raise NotFoundError("Debate not found.")
    participant = (
        await db.execute(
            select(User).where(User.id == user.id)
        )
    ).scalar_one()
    dispute = Dispute(
        debate_id=payload.debate_id,
        raised_by=user.id,
        reason=payload.reason,
        evidence=payload.evidence,
        status=DisputeStatus.open,
        payout_on_hold=True,
    )
    db.add(dispute)
    debate.status = debate.status  # keep; settlement engine will hold payout
    await record_audit(db, "dispute", actor_id=user.id, entity_type="debate", entity_id=str(debate.id))
    await db.commit()
    await db.refresh(dispute)
    return DisputeOut.model_validate(dispute)


@disputes_router.get("/mine", response_model=List[DisputeOut])
async def my_disputes(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dispute).where(Dispute.raised_by == user.id).order_by(Dispute.created_at.desc()))
    return [DisputeOut.model_validate(d) for d in result.scalars().all()]


@disputes_router.get("", response_model=List[DisputeOut])
async def all_disputes(admin: User = Depends(require_role(UserRole.moderator)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dispute).order_by(Dispute.created_at.desc()))
    return [DisputeOut.model_validate(d) for d in result.scalars().all()]


@disputes_router.post("/{dispute_id}/resolve", response_model=DisputeOut)
async def resolve_dispute(
    dispute_id: uuid.UUID,
    payload: DisputeResolve,
    admin: User = Depends(require_role(UserRole.moderator)),
    db: AsyncSession = Depends(get_db),
):
    dispute = await db.get(Dispute, dispute_id)
    if dispute is None:
        raise NotFoundError("Dispute not found.")
    dispute.status = payload.status
    dispute.resolution_notes = payload.resolution_notes
    dispute.resolved_by = admin.id
    dispute.payout_on_hold = payload.status in (DisputeStatus.open, DisputeStatus.under_review)
    from datetime import datetime, timezone

    dispute.resolved_at = datetime.now(timezone.utc)
    await record_audit(db, "dispute_resolved", actor_id=admin.id, entity_type="dispute", entity_id=str(dispute.id),
                       details={"status": payload.status.value})
    await db.commit()
    await db.refresh(dispute)
    return DisputeOut.model_validate(dispute)


# --- Games (§51) — free play by default ---

@games_router.post("", response_model=GameOut, status_code=201)
async def create_game(payload: GameCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    game = Game(game_type=payload.game_type, status=GameStatus.waiting, player_one_id=user.id, is_real_money=False)
    db.add(game)
    await db.commit()
    await db.refresh(game)
    return GameOut.model_validate(game)


@games_router.get("", response_model=List[GameOut])
async def list_games(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Game).where(
            (Game.player_one_id == user.id) | (Game.player_two_id == user.id)
        ).order_by(Game.created_at.desc())
    )
    return [GameOut.model_validate(g) for g in result.scalars().all()]


@games_router.get("/types", response_model=List[str])
async def game_types():
    return [g.value for g in GameType]
