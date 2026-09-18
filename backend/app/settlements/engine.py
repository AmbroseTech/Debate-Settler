"""Settlement engine (§80).

Handles both Local (vote-driven) and Online Result (source-driven) settlement.
Never settles on an unverified guess. Financial movements are performed inside
the caller's DB transaction using the ledger service.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.money import calculate_fee, quantize, to_decimal
from app.models.base import (
    DebateMode,
    DebateStatus,
    FinancialState,
    ParticipantRole,
    Side,
    VoteChoice,
)
from app.models.debate import Debate, DebateParticipant, DebateRules, DebateVote
from app.models.payment import SettlementRecord
from app.models.wallet import Wallet
from app.services import ledger_service, notification_service
from app.services.audit_service import record_audit


async def tally_votes(db: AsyncSession, debate_id: uuid.UUID) -> dict:
    result = await db.execute(
        select(DebateVote).where(
            DebateVote.debate_id == debate_id, DebateVote.is_valid.is_(True)
        )
    )
    votes = list(result.scalars().all())
    tally = {"side_a": 0, "side_b": 0, "draw": 0, "total": len(votes)}
    for vote in votes:
        tally[vote.choice.value] += 1
    return tally


def determine_local_winner(tally: dict, allow_draw: bool) -> str:
    a, b = tally["side_a"], tally["side_b"]
    if a > b:
        return "a"
    if b > a:
        return "b"
    return "draw" if allow_draw else "a"


async def _funded_participants(
    db: AsyncSession, debate_id: uuid.UUID
) -> Tuple[Optional[DebateParticipant], Optional[DebateParticipant]]:
    result = await db.execute(
        select(DebateParticipant).where(
            DebateParticipant.debate_id == debate_id,
            DebateParticipant.role.in_([ParticipantRole.creator, ParticipantRole.challenger]),
        )
    )
    participants = list(result.scalars().all())
    side_a = next((p for p in participants if p.side == Side.a), None)
    side_b = next((p for p in participants if p.side == Side.b), None)
    return side_a, side_b


async def _get_rules(db: AsyncSession, debate_id: uuid.UUID) -> Optional[DebateRules]:
    """Load debate rules with an explicit async query.

    Accessing `debate.rules` directly would trigger a lazy load, which is not
    allowed inside the async event loop (raises MissingGreenlet).
    """
    result = await db.execute(select(DebateRules).where(DebateRules.debate_id == debate_id))
    return result.scalar_one_or_none()


async def settle_debate(
    db: AsyncSession,
    debate: Debate,
    winner_side: str,
    *,
    source_verified: bool = True,
    settlement_source: Optional[str] = None,
    reason: Optional[str] = None,
) -> SettlementRecord:
    """Finalise a debate result and move any locked funds.

    winner_side: 'a' | 'b' | 'draw'
    """
    if debate.status == DebateStatus.settled:
        raise ConflictError("This debate has already been settled.")

    # Block settlement while a dispute holds the payout (§23).
    from app.models.base import DisputeStatus
    from app.models.notification import Dispute

    open_dispute = await db.execute(
        select(Dispute).where(
            Dispute.debate_id == debate.id,
            Dispute.status.in_([DisputeStatus.open, DisputeStatus.under_review]),
        )
    )
    if open_dispute.scalar_one_or_none() is not None:
        debate.status = DebateStatus.under_review
        await record_audit(
            db, "settlement_held_dispute", entity_type="debate", entity_id=str(debate.id)
        )
        await db.flush()
        raise ConflictError("This result is under review because of an open dispute.")

    if debate.mode == DebateMode.online and not source_verified:
        debate.status = DebateStatus.under_review
        await db.flush()
        raise ConflictError("The result source has not been verified. We never guess a winner.")

    side_a, side_b = await _funded_participants(db, debate.id)
    rules = await _get_rules(db, debate.id)
    stake = to_decimal(debate.stake_amount)
    gross_pool = quantize(stake * 2)
    fee_fraction = debate.platform_fee_percent / Decimal(100)
    platform_fee = calculate_fee(gross_pool, fee_fraction)
    winner_payout = quantize(gross_pool - platform_fee)

    settlement = SettlementRecord(
        debate_id=debate.id,
        winner_side=winner_side,
        gross_pool=gross_pool,
        platform_fee=platform_fee,
        winner_payout=winner_payout if winner_side != "draw" else stake,
        currency=debate.currency,
        status=FinancialState.completed if stake > 0 else FinancialState.pending,
        source_verified=source_verified,
        settlement_source=settlement_source or (rules.settlement_source if rules else None),
        reason=reason,
    )

    # Financial settlement only when there is a real stake.
    if stake > 0 and side_a and side_b and side_a.user_id and side_b.user_id:
        wallet_a = await ledger_service.get_or_create_wallet(db, side_a.user_id, debate.currency)
        wallet_b = await ledger_service.get_or_create_wallet(db, side_b.user_id, debate.currency)

        if winner_side == "draw":
            # Return each side's own stake per the agreed draw rule (§27).
            await ledger_service.release_stake(db, wallet_a, stake, debate_id=debate.id, description="Draw — stake returned")
            await ledger_service.release_stake(db, wallet_b, stake, debate_id=debate.id, description="Draw — stake returned")
            settlement.status = FinancialState.refunded
        else:
            winner_wallet = wallet_a if winner_side == "a" else wallet_b
            loser_wallet = wallet_b if winner_side == "a" else wallet_a
            winner_participant = side_a if winner_side == "a" else side_b
            loser_participant = side_b if winner_side == "a" else side_a

            # Winner gets their own stake back plus the loser's stake net of fee.
            await ledger_service.release_stake(
                db, winner_wallet, stake, debate_id=debate.id, description="Winner stake released"
            )
            await ledger_service.settle_stake_to_winner(
                db,
                loser_wallet=loser_wallet,
                winner_wallet=winner_wallet,
                stake_amount=stake,
                platform_fee_amount=platform_fee,
                debate_id=debate.id,
                is_demo=not settings.ENABLE_REAL_MONEY,
            )
            settlement.status = FinancialState.completed

            await _update_stats(db, winner_participant.user_id, loser_participant.user_id, winner_side == "draw")

    debate.winner_side = winner_side
    debate.status = DebateStatus.draw if winner_side == "draw" else DebateStatus.settled
    from datetime import datetime, timezone

    debate.settled_at = datetime.now(timezone.utc)
    debate.result_summary = reason or _result_summary(debate, winner_side)

    db.add(settlement)
    await record_audit(
        db, "settlement", entity_type="debate", entity_id=str(debate.id),
        details={"winner_side": winner_side, "gross_pool": str(gross_pool), "fee": str(platform_fee)},
    )

    # Notify both participants.
    for participant in (side_a, side_b):
        if participant and participant.user_id:
            await notification_service.notify_settled(
                db, participant.user_id, debate.result_summary or "Your debate result is in."
            )

    await db.flush()
    return settlement


def _result_summary(debate: Debate, winner_side: str) -> str:
    if winner_side == "draw":
        return f"“{debate.question}” ended in a draw."
    winning_label = debate.side_a_label if winner_side == "a" else debate.side_b_label
    return f"“{debate.question}” settled — {winning_label} wins."


async def _update_stats(db: AsyncSession, winner_id: uuid.UUID, loser_id: uuid.UUID, is_draw: bool) -> None:
    from app.models.user import Profile

    for user_id, field in ((winner_id, "wins"), (loser_id, "losses")):
        result = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if profile:
            if is_draw:
                profile.draws += 1
            else:
                setattr(profile, field, getattr(profile, field) + 1)


async def settle_local_by_votes(db: AsyncSession, debate: Debate) -> SettlementRecord:
    tally = await tally_votes(db, debate.id)
    rules = await _get_rules(db, debate.id)
    allow_draw = rules.allow_draw if rules else True
    winner = determine_local_winner(tally, allow_draw)
    return await settle_debate(
        db, debate, winner,
        reason=f"Votes — A: {tally['side_a']}, B: {tally['side_b']}, Draw: {tally['draw']}.",
    )
