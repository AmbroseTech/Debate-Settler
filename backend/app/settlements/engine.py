"""Community vote counting and result finalization."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.base import (
    DebateMode,
    DebateStatus,
    DisputeStatus,
    ParticipantRole,
)
from app.models.debate import Debate, DebateParticipant, DebateRules, DebateVote
from app.models.notification import Dispute
from app.services import notification_service
from app.services.audit_service import record_audit


async def tally_votes(db: AsyncSession, debate_id: uuid.UUID) -> dict:
    rows = (
        (
            await db.execute(
                select(DebateVote).where(
                    DebateVote.debate_id == debate_id, DebateVote.is_valid.is_(True)
                )
            )
        )
        .scalars()
        .all()
    )
    totals = {"side_a": 0, "side_b": 0, "draw": 0, "total": len(rows)}
    for vote in rows:
        totals[vote.choice.value] += 1
    return totals


def determine_local_winner(tally: dict, allow_draw: bool) -> str:
    if tally["side_a"] == tally["side_b"]:
        return "draw" if allow_draw else "a"
    return "a" if tally["side_a"] > tally["side_b"] else "b"


async def settle_debate(
    db: AsyncSession,
    debate: Debate,
    winner_side: str,
    *,
    source_verified: bool = True,
    settlement_source: str | None = None,
    reason: str | None = None,
) -> Debate:
    if debate.status in (DebateStatus.settled, DebateStatus.draw):
        raise ConflictError("This debate already has a result.")
    if debate.mode == DebateMode.online and not source_verified:
        debate.status = DebateStatus.under_review
        raise ConflictError("The result source has not been verified.")
    dispute = await db.execute(
        select(Dispute).where(
            Dispute.debate_id == debate.id,
            Dispute.status.in_([DisputeStatus.open, DisputeStatus.under_review]),
        )
    )
    if dispute.scalar_one_or_none():
        debate.status = DebateStatus.under_review
        raise ConflictError("This result is under review because of an open report.")
    debate.winner_side = winner_side
    debate.status = DebateStatus.draw if winner_side == "draw" else DebateStatus.settled
    debate.settled_at = datetime.now(timezone.utc)
    label = (
        "a draw"
        if winner_side == "draw"
        else debate.side_a_label
        if winner_side == "a"
        else debate.side_b_label
    )
    debate.result_summary = (
        reason or f"“{debate.question}” was settled by the community: {label}."
    )
    await record_audit(
        db,
        "debate_result",
        entity_type="debate",
        entity_id=str(debate.id),
        details={"winner_side": winner_side, "source_verified": source_verified},
    )
    participants = (
        (
            await db.execute(
                select(DebateParticipant).where(
                    DebateParticipant.debate_id == debate.id,
                    DebateParticipant.role.in_(
                        [ParticipantRole.creator, ParticipantRole.challenger]
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    for participant in participants:
        if participant.user_id:
            await notification_service.notify_settled(
                db, participant.user_id, debate.result_summary
            )
    await db.flush()
    return debate


async def settle_local_by_votes(db: AsyncSession, debate: Debate) -> Debate:
    totals = await tally_votes(db, debate.id)
    rules = (
        await db.execute(select(DebateRules).where(DebateRules.debate_id == debate.id))
    ).scalar_one_or_none()
    minimum = max(3, rules.required_voters if rules else 3)
    if totals["total"] < minimum:
        debate.status = DebateStatus.closed
        return debate
    winner = determine_local_winner(totals, rules.allow_draw if rules else True)
    return await settle_debate(db, debate, winner)
