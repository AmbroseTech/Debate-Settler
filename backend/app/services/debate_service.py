"""Debate service: creation wizard, invitations, voting, locking (§10-§22).

The backend is the source of truth for rules, votes, deadlines and stakes.
Once a debate is locked its core terms are immutable (§81). Time comparisons
always use the server clock, never the client's (§14).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    DebateLockedError,
    NotFoundError,
    ValidationError,
)
from app.core.money import to_decimal
from app.core.security import generate_token_urlsafe
from app.models.base import (
    DebateMode,
    DebateStatus,
    ParticipantRole,
    Side,
    VoteChoice,
)
from app.models.category import Category
from app.models.debate import (
    Debate,
    DebateEvent,
    DebateInvitation,
    DebateParticipant,
    DebateRules,
    DebateVote,
)
from app.models.user import User
from app.schemas.debate import DebateCreate
from app.services import ledger_service, notification_service, wallet_service
from app.services.audit_service import record_audit
from app.settlements import engine


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _add_event(
    db: AsyncSession, debate_id: uuid.UUID, event_type: str,
    actor_id: Optional[uuid.UUID] = None, payload: Optional[str] = None,
) -> None:
    db.add(DebateEvent(debate_id=debate_id, event_type=event_type, actor_id=actor_id, payload=payload))


async def create_debate(db: AsyncSession, user: User, data: DebateCreate) -> Debate:
    if data.mode == DebateMode.online and not data.rules.settlement_source:
        raise ValidationError(
            "An Online Result Debate needs an agreed settlement source before it can be created."
        )
    if data.stake_amount > 0 and not (settings.ENABLE_REAL_MONEY or settings.PAYMENT_MODE == "demo"):
        raise ConflictError("Stakes are not enabled in this configuration.")

    debate = Debate(
        creator_id=user.id,
        category_id=data.category_id,
        mode=data.mode,
        status=DebateStatus.draft,
        question=data.question,
        side_a_label=data.side_a_label,
        side_b_label=data.side_b_label,
        is_public=data.is_public,
        start_at=data.start_at,
        end_at=data.end_at,
        stake_amount=to_decimal(data.stake_amount),
        currency=data.currency or settings.DEFAULT_CURRENCY,
        platform_fee_percent=settings.PLATFORM_FEE_PERCENT,
    )
    db.add(debate)
    await db.flush()

    rules = DebateRules(debate_id=debate.id, **data.rules.model_dump())
    db.add(rules)

    # Creator is Side A until an opponent joins as Side B.
    db.add(
        DebateParticipant(
            debate_id=debate.id, user_id=user.id,
            role=ParticipantRole.creator, side=Side.a, confirmed=True, joined_at=_now(),
        )
    )
    await _add_event(db, debate.id, "created", actor_id=user.id)
    await record_audit(
        db, "debate_creation", actor_id=user.id, entity_type="debate", entity_id=str(debate.id),
        details={"mode": data.mode.value, "stake": str(debate.stake_amount)},
    )

    # Increment creator's debates_created stat.
    from app.models.user import Profile

    prof = (await db.execute(select(Profile).where(Profile.user_id == user.id))).scalar_one_or_none()
    if prof:
        prof.debates_created += 1

    await db.flush()
    return debate


async def get_debate(db: AsyncSession, debate_id: uuid.UUID) -> Debate:
    # Eager-load relationships so serialization never triggers a lazy load
    # inside the async event loop (which would raise MissingGreenlet).
    result = await db.execute(
        select(Debate)
        .where(Debate.id == debate_id)
        .options(
            selectinload(Debate.rules),
            selectinload(Debate.participants),
            selectinload(Debate.votes),
            selectinload(Debate.invitations),
        )
    )
    debate = result.scalar_one_or_none()
    if debate is None:
        raise NotFoundError("Debate not found.")
    return debate


async def create_invitation(
    db: AsyncSession, debate: Debate, kind: str, max_uses: int,
    expires_in_hours: int, invited_email: Optional[str] = None,
) -> DebateInvitation:
    if debate.locked_at is not None:
        raise DebateLockedError()
    token = generate_token_urlsafe(24)
    invitation = DebateInvitation(
        debate_id=debate.id,
        token=token,
        kind=kind,
        invited_email=invited_email,
        max_uses=max_uses,
        expires_at=_now() + timedelta(hours=expires_in_hours),
    )
    db.add(invitation)
    await _add_event(db, debate.id, f"invitation_created:{kind}")
    await db.flush()
    return invitation


def build_share_links(base_url: str, token: str) -> dict:
    url = f"{base_url}/join/{token}"
    text = "Join my debate on Debate_Settler"
    from urllib.parse import quote

    return {
        "whatsapp": f"https://wa.me/?text={quote(text + ' ' + url)}",
        "telegram": f"https://t.me/share/url?url={quote(url)}&text={quote(text)}",
        "facebook": f"https://www.facebook.com/sharer/sharer.php?u={quote(url)}",
        "x": f"https://twitter.com/intent/tweet?url={quote(url)}&text={quote(text)}",
        "email": f"mailto:?subject={quote(text)}&body={quote(url)}",
        "copy_link": url,
        "qr_code": f"{base_url}/api/v1/invitations/qr?token={token}",
    }


async def accept_invitation(db: AsyncSession, token: str, user: User) -> DebateInvitation:
    result = await db.execute(select(DebateInvitation).where(DebateInvitation.token == token))
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise NotFoundError("This invitation link is not valid.")
    if invitation.used or (invitation.expires_at and invitation.expires_at < _now()):
        raise ConflictError("This invitation has expired or already been used.")
    if invitation.use_count >= invitation.max_uses:
        raise ConflictError("This invitation has reached its usage limit.")

    debate = await get_debate(db, invitation.debate_id)
    if invitation.kind == "opponent":
        await _join_as_opponent(db, debate, user)
    else:
        await _join_as_voter(db, debate, user, invitation)

    invitation.use_count += 1
    if invitation.use_count >= invitation.max_uses:
        invitation.used = True
    invitation.accepted_by = user.id
    await _add_event(db, debate.id, f"invitation_accepted:{invitation.kind}", actor_id=user.id)

    # Notify the creator.
    await notification_service.notify(
        db, debate.creator_id, "Your debate invitation was accepted",
        f"{user.username} accepted your invitation to “{debate.question}”.",
        category="debate",
    )
    await db.flush()
    return invitation


async def _join_as_opponent(db: AsyncSession, debate: Debate, user: User) -> None:
    if debate.locked_at is not None:
        raise DebateLockedError()
    existing = await db.execute(
        select(DebateParticipant).where(
            DebateParticipant.debate_id == debate.id,
            DebateParticipant.role == ParticipantRole.challenger,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("This debate already has an opponent.")
    if user.id == debate.creator_id:
        raise ConflictError("You can't challenge your own debate.")

    db.add(
        DebateParticipant(
            debate_id=debate.id, user_id=user.id,
            role=ParticipantRole.challenger, side=Side.b, joined_at=_now(),
        )
    )
    if debate.status == DebateStatus.open or debate.status == DebateStatus.draft:
        debate.status = DebateStatus.payment_pending if debate.stake_amount > 0 else DebateStatus.active
    from app.models.user import Profile

    prof = (await db.execute(select(Profile).where(Profile.user_id == user.id))).scalar_one_or_none()
    if prof:
        prof.debates_participated += 1


async def _join_as_voter(db: AsyncSession, debate: Debate, user: User, invitation: DebateInvitation) -> None:
    if debate.mode != DebateMode.local:
        raise ConflictError("Only local debates accept voters.")
    existing = await db.execute(
        select(DebateParticipant).where(
            DebateParticipant.debate_id == debate.id,
            DebateParticipant.user_id == user.id,
            DebateParticipant.role == ParticipantRole.voter,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return  # idempotent
    db.add(
        DebateParticipant(
            debate_id=debate.id, user_id=user.id,
            role=ParticipantRole.voter, joined_at=_now(),
        )
    )


async def confirm_side(db: AsyncSession, debate: Debate, user: User, side: Side) -> None:
    if debate.locked_at is not None:
        raise DebateLockedError()
    result = await db.execute(
        select(DebateParticipant).where(
            DebateParticipant.debate_id == debate.id,
            DebateParticipant.user_id == user.id,
            DebateParticipant.role.in_([ParticipantRole.creator, ParticipantRole.challenger]),
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        raise NotFoundError("You are not a participant in this debate.")
    participant.confirmed = True
    participant.side = side
    await _add_event(db, debate.id, f"side_confirmed:{side.value}", actor_id=user.id)
    await record_audit(db, "debate_side_confirmed", actor_id=user.id, entity_type="debate", entity_id=str(debate.id))
    await db.flush()


async def fund_stake(db: AsyncSession, debate: Debate, user: User) -> None:
    """Lock this participant's stake for a financial debate (§24)."""
    if debate.locked_at is not None:
        raise DebateLockedError()
    if debate.stake_amount <= 0:
        raise ConflictError("This debate has no financial stake.")
    result = await db.execute(
        select(DebateParticipant).where(
            DebateParticipant.debate_id == debate.id, DebateParticipant.user_id == user.id,
            DebateParticipant.role.in_([ParticipantRole.creator, ParticipantRole.challenger]),
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        raise NotFoundError("You are not a participant in this debate.")
    if participant.has_funded:
        return
    wallet = await wallet_service.get_wallet(db, user.id)
    await ledger_service.lock_stake(
        db, wallet, debate.stake_amount, debate_id=debate.id,
        description=f"Stake for “{debate.question}”",
        idempotency_key=f"stake:{debate.id}:{user.id}",
    )
    participant.has_funded = True
    await _add_event(db, debate.id, "stake_funded", actor_id=user.id)
    await db.flush()


async def lock_debate(db: AsyncSession, debate: Debate, actor: User) -> Debate:
    """Lock a debate once both sides have confirmed (and funded, if a stake)."""
    if debate.locked_at is not None:
        raise DebateLockedError()

    participants = (
        await db.execute(
            select(DebateParticipant).where(
                DebateParticipant.debate_id == debate.id,
                DebateParticipant.role.in_([ParticipantRole.creator, ParticipantRole.challenger]),
            )
        )
    ).scalars().all()
    sides = {p.side for p in participants}
    if Side.a not in sides or Side.b not in sides:
        raise ConflictError("Both sides must join before the debate can be locked.")
    if not all(p.confirmed for p in participants):
        raise ConflictError("Both sides must confirm the rules before locking.")
    if debate.stake_amount > 0 and not all(p.has_funded for p in participants):
        raise ConflictError("Both sides must fund their stake before locking.")
    if debate.mode == DebateMode.online and (not debate.rules or not debate.rules.settlement_source):
        raise ValidationError("An Online Result Debate needs a settlement source before locking.")

    debate.locked_at = _now()
    debate.status = DebateStatus.active
    await _add_event(db, debate.id, "locked", actor_id=actor.id)
    await record_audit(db, "debate_locking", actor_id=actor.id, entity_type="debate", entity_id=str(debate.id))
    await db.flush()
    return debate


async def cast_vote(db: AsyncSession, debate: Debate, user: User, choice: VoteChoice) -> Tuple[bool, str]:
    if debate.mode != DebateMode.local:
        raise ConflictError("Only local debates use audience voting.")
    now = _now()
    if debate.start_at and now < debate.start_at:
        raise ConflictError("Voting hasn't started yet.")
    if debate.end_at and now > debate.end_at:
        raise ConflictError("Voting has closed.")
    if debate.status not in (DebateStatus.active, DebateStatus.voting, DebateStatus.closing_soon):
        raise ConflictError("This debate isn't accepting votes right now.")

    # Voter must be a registered participant (via invitation) — §17.
    is_voter = (
        await db.execute(
            select(DebateParticipant).where(
                DebateParticipant.debate_id == debate.id,
                DebateParticipant.user_id == user.id,
                DebateParticipant.role == ParticipantRole.voter,
            )
        )
    ).scalar_one_or_none()
    if is_voter is None:
        raise ConflictError("You need a valid invitation to vote in this debate.")

    existing = (
        await db.execute(
            select(DebateVote).where(
                DebateVote.debate_id == debate.id, DebateVote.voter_id == user.id
            )
        )
    ).scalar_one_or_none()

    allow_change = debate.rules.allow_vote_change if debate.rules else False
    if existing is not None:
        if not allow_change:
            raise ConflictError("You've already voted. Votes can't be changed in this debate.")
        existing.choice = choice
        existing.changed = True
        await _add_event(db, debate.id, "vote_changed", actor_id=user.id)
        await db.flush()
        return True, "Your vote has been updated."

    db.add(DebateVote(debate_id=debate.id, voter_id=user.id, choice=choice, is_valid=True))
    await _add_event(db, debate.id, "vote_cast", actor_id=user.id)
    await record_audit(db, "vote_submission", actor_id=user.id, entity_type="debate", entity_id=str(debate.id))
    await db.flush()
    return True, "Your vote has been recorded."


async def vote_counts(db: AsyncSession, debate: Debate, reveal: bool) -> dict:
    tally = await engine.tally_votes(db, debate.id)
    rules = (
        await db.execute(select(DebateRules).where(DebateRules.debate_id == debate.id))
    ).scalar_one_or_none()
    required = rules.required_voters if rules else 0
    votes_public = rules.votes_public if rules else True
    revealed = reveal or votes_public or debate.status in (
        DebateStatus.closed, DebateStatus.settled, DebateStatus.draw,
    )
    return {
        "side_a": tally["side_a"] if revealed else 0,
        "side_b": tally["side_b"] if revealed else 0,
        "draw": tally["draw"] if revealed else 0,
        "total": tally["total"],
        "required": required,
        "revealed": revealed,
    }


# --- Listing / trending / search (§46, §47) ---

async def list_debates(
    db: AsyncSession,
    *,
    status: Optional[DebateStatus] = None,
    mode: Optional[DebateMode] = None,
    category_id: Optional[uuid.UUID] = None,
    public_only: bool = True,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Debate], int]:
    query = select(Debate)
    if public_only:
        query = query.where(Debate.is_public.is_(True))
    if status:
        query = query.where(Debate.status == status)
    if mode:
        query = query.where(Debate.mode == mode)
    if category_id:
        query = query.where(Debate.category_id == category_id)
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(Debate.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total


async def trending_debates(db: AsyncSession, limit: int = 10) -> List[Debate]:
    """Traditional engagement ranking — no AI (§46).

    Score = views + 3*shares + 2*comments + participants-weighted freshness.
    Cached by the caller in Redis.
    """
    result = await db.execute(
        select(Debate).where(Debate.is_public.is_(True)).limit(200)
    )
    debates = list(result.scalars().all())

    def score(d: Debate) -> float:
        freshness = 1.0
        age_days = (_now() - d.created_at).days if d.created_at else 0
        if age_days <= 7:
            freshness = 1.5
        elif age_days > 30:
            freshness = 0.5
        return (d.views + 3 * d.shares + 2 * d.comments_count) * freshness

    debates.sort(key=score, reverse=True)
    return debates[:limit]


async def search_debates(db: AsyncSession, term: str, limit: int = 20, offset: int = 0) -> Tuple[List[Debate], int]:
    pattern = f"%{term}%"
    query = select(Debate).where(
        Debate.is_public.is_(True),
        (Debate.question.ilike(pattern))
        | (Debate.side_a_label.ilike(pattern))
        | (Debate.side_b_label.ilike(pattern)),
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(query.order_by(Debate.created_at.desc()).limit(limit).offset(offset))
    return list(result.scalars().all()), total
