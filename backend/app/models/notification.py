"""Notifications, disputes, audit logs and games."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    BaseModel,
    DisputeStatus,
    GameStatus,
    GameType,
    NotificationChannel,
)


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, native_enum=False), default=NotificationChannel.in_app, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Dispute(BaseModel):
    __tablename__ = "disputes"

    debate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debates.id"), index=True, nullable=False
    )
    raised_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # links / description
    status: Mapped[DisputeStatus] = mapped_column(
        Enum(DisputeStatus, native_enum=False), default=DisputeStatus.open, index=True, nullable=False
    )
    payout_on_hold: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(BaseModel):
    """Tamper-resistant, traceable record of important actions (§44)."""

    __tablename__ = "audit_logs"

    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Hash chain link to make the log tamper-evident.
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class Game(BaseModel):
    __tablename__ = "games"

    game_type: Mapped[GameType] = mapped_column(Enum(GameType, native_enum=False), nullable=False, index=True)
    status: Mapped[GameStatus] = mapped_column(Enum(GameStatus, native_enum=False), default=GameStatus.waiting, nullable=False)
    player_one_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    player_two_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_real_money: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # free play only by default
    state: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON game state
    current_turn: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    winner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
