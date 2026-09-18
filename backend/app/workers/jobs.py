"""Background worker jobs (§63).

Jobs are idempotent and retry-safe. A lightweight scheduler loop runs periodic
tasks: closing debates whose end time passed, settling local debates by votes,
handling funding timeouts, expiring invitations and verifying pending payments.

In production these can be moved to a real queue (e.g. Celery/RQ/Dramatiq) —
the job functions are plain async callables so the transport is swappable.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.base import (
    DebateMode,
    DebateStatus,
    ParticipantRole,
)
from app.models.debate import Debate, DebateInvitation, DebateParticipant
from app.services import ledger_service, notification_service, wallet_service
from app.settlements import engine

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def close_expired_debates() -> int:
    """Stop accepting votes past the agreed end time and settle local debates (§20)."""
    closed = 0
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Debate).where(
                Debate.end_at.is_not(None),
                Debate.end_at <= _now(),
                Debate.status.in_([DebateStatus.active, DebateStatus.voting, DebateStatus.closing_soon]),
            )
        )
        for debate in result.scalars().all():
            debate.status = DebateStatus.closed
            if debate.mode == DebateMode.local:
                try:
                    await engine.settle_local_by_votes(db, debate)
                except Exception as exc:  # keep loop resilient
                    logger.error("local_settle_failed", debate_id=str(debate.id), error=str(exc))
            else:
                debate.status = DebateStatus.being_verified
            closed += 1
        await db.commit()
    return closed


async def handle_funding_timeouts() -> int:
    """Cancel two-sided debates where one side funded and the other didn't (§26)."""
    handled = 0
    timeout = timedelta(minutes=settings.FUNDING_TIMEOUT_MINUTES)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Debate).where(
                Debate.status == DebateStatus.payment_pending,
                Debate.stake_amount > 0,
                Debate.updated_at <= _now() - timeout,
            )
        )
        for debate in result.scalars().all():
            participants = (
                await db.execute(
                    select(DebateParticipant).where(
                        DebateParticipant.debate_id == debate.id,
                        DebateParticipant.role.in_([ParticipantRole.creator, ParticipantRole.challenger]),
                    )
                )
            ).scalars().all()

            funded = [p for p in participants if p.has_funded]
            if len(funded) == len(participants) and participants:
                # Both funded — proceed to active instead of cancelling.
                debate.status = DebateStatus.active
                continue

            # Refund anyone who funded, then cancel.
            for p in funded:
                if p.user_id:
                    wallet = await ledger_service.get_or_create_wallet(db, p.user_id, debate.currency)
                    await ledger_service.release_stake(
                        db, wallet, debate.stake_amount, debate_id=debate.id,
                        description="Funding timeout — stake returned",
                    )
                    await notification_service.notify(
                        db, p.user_id, "Debate cancelled",
                        f"“{debate.question}” was cancelled because the other side didn't fund in time. "
                        "Your stake has been returned.",
                        category="wallet",
                    )
            debate.status = DebateStatus.funding_timeout
            handled += 1
        await db.commit()
    return handled


async def expire_invitations() -> int:
    expired = 0
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DebateInvitation).where(
                DebateInvitation.used.is_(False),
                DebateInvitation.expires_at.is_not(None),
                DebateInvitation.expires_at <= _now(),
            )
        )
        for inv in result.scalars().all():
            inv.used = True
            expired += 1
        await db.commit()
    return expired


async def verify_pending_payments() -> int:
    """Re-check deposits/withdrawals left in a pending state (§63)."""
    from app.models.payment import Deposit, Withdrawal
    from app.models.base import DepositStatus, WithdrawalStatus

    verified = 0
    async with AsyncSessionLocal() as db:
        deposits = (
            await db.execute(select(Deposit).where(Deposit.status == DepositStatus.pending).limit(50))
        ).scalars().all()
        for dep in deposits:
            await wallet_service.verify_deposit(db, dep.id)
            verified += 1
        withdrawals = (
            await db.execute(select(Withdrawal).where(Withdrawal.status == WithdrawalStatus.processing).limit(50))
        ).scalars().all()
        for wd in withdrawals:
            await wallet_service.check_withdrawal_status(db, wd.id)
            verified += 1
        await db.commit()
    return verified


JOBS = [
    (30, close_expired_debates),
    (60, handle_funding_timeouts),
    (300, expire_invitations),
    (60, verify_pending_payments),
]


async def _run_job(name: str, fn) -> None:
    try:
        count = await fn()
        if count:
            logger.info("worker_job", job=name, affected=count)
    except Exception as exc:
        logger.error("worker_job_failed", job=name, error=str(exc))


async def run_scheduler(once: bool = False) -> None:
    """Run all jobs on their intervals. `once=True` runs a single pass (tests)."""
    if once:
        for _interval, fn in JOBS:
            await _run_job(fn.__name__, fn)
        return
    last_run = {fn: 0.0 for _interval, fn in JOBS}
    logger.info("worker_scheduler_started")
    while True:
        now = asyncio.get_event_loop().time()
        for interval, fn in JOBS:
            if now - last_run[fn] >= interval:
                await _run_job(fn.__name__, fn)
                last_run[fn] = now
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_scheduler())
