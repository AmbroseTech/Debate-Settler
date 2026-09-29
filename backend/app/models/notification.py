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
    Integer,
    String,
    Text,
    UniqueConstraint,
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
    state: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON game state
    current_turn: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    winner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # Set once a verified result has been applied to the leaderboards, so the
    # same match can never award rating/stats twice (§7.1).
    resulted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class GameInvitation(BaseModel):
    """A challenge to play a specific multiplayer match (§6, §8).

    A secure opaque token — never a DB id — authorises a recipient to accept
    (§16). `to_username`, when set, restricts the invitation to that player.
    """

    __tablename__ = "game_invitations"

    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    from_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    to_username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class GameStanding(BaseModel):
    """Per-game, per-player ranking persisted in the DB (§7). Survives restarts."""

    __tablename__ = "game_standings"
    __table_args__ = (
        UniqueConstraint("game_type", "user_id", name="uq_standing_game_user"),
    )

    game_type: Mapped[GameType] = mapped_column(Enum(GameType, native_enum=False), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=1200, nullable=False, index=True)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
