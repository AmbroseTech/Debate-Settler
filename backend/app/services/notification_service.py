"""Notification service.

Creates in-app notifications immediately and enqueues email/SMS/push delivery
through the background worker.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.base import NotificationChannel
from app.models.notification import Notification

logger = get_logger(__name__)


async def notify(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str,
    body: str,
    *,
    category: str = "general",
    link: Optional[str] = None,
    channel: NotificationChannel = NotificationChannel.in_app,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        body=body,
        category=category,
        link=link,
        channel=channel,
    )
    db.add(notification)
    await db.flush()
    logger.info("notification_created", user_id=str(user_id), category=category)
    return notification


async def notify_debate_starting(db: AsyncSession, user_id: uuid.UUID, debate_question: str) -> None:
    await notify(
        db, user_id, "Your debate is starting soon",
        f"“{debate_question}” starts shortly. Get ready!",
        category="debate",
    )


async def notify_voting_open(db: AsyncSession, user_id: uuid.UUID, debate_question: str) -> None:
    await notify(
        db, user_id, "Voting is now open",
        f"Cast your vote in “{debate_question}”.", category="debate",
    )


async def notify_settled(db: AsyncSession, user_id: uuid.UUID, message: str) -> None:
    await notify(
        db, user_id, "Your debate has been settled",
        message, category="settlement",
    )

