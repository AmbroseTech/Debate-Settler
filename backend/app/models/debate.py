"""Debate, rules, participants, votes, invitations and debate events.

These tables encode the two debate modes (§9): LOCAL and ONLINE RESULT. Once a
debate is locked, its core settlement terms become immutable (§81).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    BaseModel,
    DebateMode,
    DebateStatus,
    ParticipantRole,
    Side,
    VoteChoice,
)


class Debate(BaseModel):
    __tablename__ = "debates"

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), index=True, nullable=True
    )
    mode: Mapped[DebateMode] = mapped_column(Enum(DebateMode), nullable=False, index=True)
    status: Mapped[DebateStatus] = mapped_column(
        Enum(DebateStatus), default=DebateStatus.draft, nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    side_a_label: Mapped[str] = mapped_column(String(200), nullable=False)
    side_b_label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Stakes (currency minor-unit-safe NUMERIC). Zero => free/social debate.
    stake_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UGX", nullable=False)
    platform_fee_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("5.00"), nullable=False)

    # Result
    winner_side: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # a | b | draw
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Engagement counters (traditional trending, §46 — no AI)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rules: Mapped["DebateRules"] = relationship(
        back_populates="debate", uselist=False, cascade="all, delete-orphan"
    )
    participants: Mapped[List["DebateParticipant"]] = relationship(
        back_populates="debate", cascade="all, delete-orphan"
    )
    votes: Mapped[List["DebateVote"]] = relationship(
        back_populates="debate", cascade="all, delete-orphan"
    )
    invitations: Mapped[List["DebateInvitation"]] = relationship(
        back_populates="debate", cascade="all, delete-orphan"
    )
    events: Mapped[List["DebateEvent"]] = relationship(
        back_populates="debate", cascade="all, delete-orphan"
    )


class DebateRules(BaseModel):
    __tablename__ = "debate_rules"

    debate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debates.id", ondelete="CASCADE"), unique=True, index=True
    )
    # Local debate rules
    required_voters: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    votes_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_draw: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_vote_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    draw_returns_stakes: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    venue: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    meeting_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    expose_address: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Online result debate rules
    settlement_source: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    settlement_rule: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    debate: Mapped["Debate"] = relationship(back_populates="rules")


class DebateParticipant(BaseModel):
    __tablename__ = "debate_participants"

    debate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debates.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=True
    )
    role: Mapped[ParticipantRole] = mapped_column(Enum(ParticipantRole), nullable=False)
    side: Mapped[Optional[Side]] = mapped_column(Enum(Side), nullable=True)
    has_funded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    debate: Mapped["Debate"] = relationship(back_populates="participants")


class DebateVote(BaseModel):
    __tablename__ = "debate_votes"

    debate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debates.id", ondelete="CASCADE"), index=True
    )
    voter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    choice: Mapped[VoteChoice] = mapped_column(Enum(VoteChoice), nullable=False)
    invitation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debate_invitations.id"), nullable=True
    )
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    debate: Mapped["Debate"] = relationship(back_populates="votes")


class DebateInvitation(BaseModel):
    __tablename__ = "debate_invitations"

    debate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debates.id", ondelete="CASCADE"), index=True
    )
    # Secure opaque token; never expose DB ids in public URLs (§16).
    token: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="voter", nullable=False)  # voter | opponent
    invited_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    accepted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    debate: Mapped["Debate"] = relationship(back_populates="invitations")


class DebateEvent(BaseModel):
    """Append-only timeline of what happened to a debate (audit-friendly)."""

    __tablename__ = "debate_events"

    debate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debates.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    debate: Mapped["Debate"] = relationship(back_populates="events")
