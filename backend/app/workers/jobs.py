"""Periodic debate close, reminder and invitation expiry jobs."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.base import DebateMode, DebateStatus
from app.models.debate import Debate, DebateInvitation, DebateParticipant
from app.models.notification import Notification
from app.services import notification_service
from app.settlements import engine

logger = get_logger(__name__)

# Statuses where a scheduled debate is still "upcoming / running" and worth
# reminding about.
_LIVE_STATUSES = [
    DebateStatus.draft, DebateStatus.open, DebateStatus.active,
    DebateStatus.voting, DebateStatus.closing_soon,
]


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


async def _audience(db, debate_id: uuid.UUID, creator_id: uuid.UUID) -> set[uuid.UUID]:
    """Everyone we should nudge: the creator plus every identified participant."""
    ids = {creator_id}
    rows = (await db.execute(select(DebateParticipant.user_id).where(
        DebateParticipant.debate_id == debate_id, DebateParticipant.user_id.is_not(None),
    ))).scalars().all()
    ids.update(r for r in rows if r)
    return ids


async def _remind(db, user_id: uuid.UUID, category: str, title: str, body: str, link: str) -> bool:
    """Send a reminder at most once per user per debate per category.
    Returns True if a new notification was created."""
    already = (await db.execute(select(Notification.id).where(
        Notification.user_id == user_id,
        Notification.category == category,
        Notification.link == link,
    ).limit(1))).scalar_one_or_none()
    if already is not None:
        return False
    await notification_service.notify(db, user_id, title, body, category=category, link=link)
    return True


async def send_reminders() -> int:
    """Timezone-aware reminders (§9): tomorrow, 1 hour, starting now, ended."""
    now = datetime.now(timezone.utc)
    sent = 0
    async with AsyncSessionLocal() as db:
        debates = (await db.execute(select(Debate).where(
            Debate.status.in_(_LIVE_STATUSES), Debate.start_at.is_not(None),
        ))).scalars().all()
        for debate in debates:
            start = debate.start_at
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            until_start = start - now
            link = f"/debates/{debate.id}"
            audience = await _audience(db, debate.id, debate.creator_id)

            if timedelta(0) < until_start <= timedelta(hours=1):
                stage, title = "1h", "Starting in 1 hour"
            elif timedelta(hours=1) < until_start <= timedelta(days=1):
                stage, title = "tomorrow", "Happens tomorrow"
            elif timedelta(days=-5) <= until_start <= timedelta(0):
                stage, title = "starting", "Starting now"
            else:
                continue

            for uid in audience:
                if await _remind(db, uid, f"reminder_{stage}", title,
                                 f"“{debate.question}” — {title}.", link):
                    sent += 1
            await db.commit()

        # Ended: notify once the poll window has closed (before the close job flips status).
        ended = (await db.execute(select(Debate).where(
            Debate.status.in_([DebateStatus.active, DebateStatus.voting, DebateStatus.closing_soon]),
            Debate.end_at.is_not(None), Debate.end_at <= now,
        ))).scalars().all()
        for debate in ended:
            link = f"/debates/{debate.id}"
            for uid in await _audience(db, debate.id, debate.creator_id):
                if await _remind(db, uid, "reminder_ended", "Debate ended",
                                 f"“{debate.question}” has closed. Results are on the way.", link):
                    sent += 1
            await db.commit()
    return sent


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


JOBS = [(30, close_expired_debates), (60, send_reminders), (300, expire_invitations)]


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
