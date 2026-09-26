"""Periodic debate close and invitation expiry jobs."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.base import DebateMode, DebateStatus
from app.models.debate import Debate, DebateInvitation
from app.settlements import engine

logger = get_logger(__name__)


async def close_expired_debates() -> int:
    closed = 0
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Debate).where(
            Debate.end_at.is_not(None), Debate.end_at <= datetime.now(timezone.utc),
            Debate.status.in_([DebateStatus.active, DebateStatus.voting, DebateStatus.closing_soon]),
        ))).scalars().all()
        for debate in rows:
            debate.status = DebateStatus.closed
            if debate.mode == DebateMode.local:
                await engine.settle_local_by_votes(db, debate)
            else:
                debate.status = DebateStatus.being_verified
            closed += 1
        await db.commit()
    return closed


async def expire_invitations() -> int:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(DebateInvitation).where(
            DebateInvitation.used.is_(False), DebateInvitation.expires_at.is_not(None),
            DebateInvitation.expires_at <= datetime.now(timezone.utc),
        ))).scalars().all()
        for row in rows:
            row.used = True
        await db.commit()
        return len(rows)


JOBS = [(30, close_expired_debates), (300, expire_invitations)]


async def run_scheduler(once: bool = False) -> None:
    if once:
        for _interval, fn in JOBS:
            await fn()
        return
    last_run = {fn: 0.0 for _interval, fn in JOBS}
    while True:
        now = asyncio.get_event_loop().time()
        for interval, fn in JOBS:
            if now - last_run[fn] >= interval:
                try:
                    await fn()
                except Exception:
                    logger.exception("worker_job_failed", job=fn.__name__)
                last_run[fn] = now
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_scheduler())
