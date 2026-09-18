"""Debate schemas: creation, rules, participants, votes, invitations."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import DebateMode, DebateStatus, ParticipantRole, Side, VoteChoice


# --- Rules ---

class DebateRulesIn(BaseModel):
    # Local
    required_voters: int = Field(0, ge=0, le=100000)
    votes_public: bool = True
    allow_draw: bool = True
    allow_vote_change: bool = False
    draw_returns_stakes: bool = True
    venue: Optional[str] = Field(None, max_length=300)
    city: Optional[str] = Field(None, max_length=120)
    country: Optional[str] = Field(None, max_length=120)
    meeting_link: Optional[str] = Field(None, max_length=500)
    expose_address: bool = False
    # Online
    settlement_source: Optional[str] = Field(None, max_length=300)
    settlement_rule: Optional[str] = None
    event_date: Optional[datetime] = None


class DebateRulesOut(DebateRulesIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


# --- Create / update ---

class DebateCreate(BaseModel):
    mode: DebateMode
    question: str = Field(..., min_length=3, max_length=500)
    side_a_label: str = Field(..., min_length=1, max_length=200)
    side_b_label: str = Field(..., min_length=1, max_length=200)
    category_id: Optional[uuid.UUID] = None
    is_public: bool = True
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    stake_amount: Decimal = Field(Decimal("0.00"), ge=0)
    currency: str = Field("UGX", max_length=3)
    rules: DebateRulesIn


class DebateParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    role: ParticipantRole
    side: Optional[Side] = None
    has_funded: bool = False
    confirmed: bool = False
    username: Optional[str] = None


class DebateBrief(BaseModel):
    """Compact representation used in lists / cards (§48)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mode: DebateMode
    status: DebateStatus
    question: str
    side_a_label: str
    side_b_label: str
    stake_amount: Decimal
    currency: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    views: int = 0
    winner_side: Optional[str] = None
    category_name: Optional[str] = None
    participants_count: int = 0
    votes_count: int = 0
    required_voters: int = 0
    settlement_source: Optional[str] = None
    venue_city: Optional[str] = None


class DebateDetail(DebateBrief):
    platform_fee_percent: Decimal
    is_public: bool
    locked_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    result_summary: Optional[str] = None
    shares: int = 0
    comments_count: int = 0
    rules: Optional[DebateRulesOut] = None
    participants: List[DebateParticipantOut] = []
    vote_tally: Optional[dict] = None
    my_side: Optional[Side] = None
    my_role: Optional[ParticipantRole] = None
    has_voted: Optional[VoteChoice] = None


class VoteCounts(BaseModel):
    side_a: int = 0
    side_b: int = 0
    draw: int = 0
    total: int = 0
    required: int = 0
    revealed: bool = False


class CastVoteRequest(BaseModel):
    choice: VoteChoice


class CastVoteResponse(BaseModel):
    recorded: bool
    message: str
    counts: Optional[VoteCounts] = None


# --- Invitations ---

class CreateInvitationRequest(BaseModel):
    kind: str = Field("voter", pattern="^(voter|opponent)$")
    invited_email: Optional[str] = None
    max_uses: int = Field(1, ge=1, le=10000)
    expires_in_hours: int = Field(72, ge=1, le=720)


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token: str
    kind: str
    invite_url: str
    max_uses: int
    use_count: int
    expires_at: Optional[datetime] = None
    used: bool


class AcceptInvitationRequest(BaseModel):
    token: str


class AcceptInvitationResponse(BaseModel):
    message: str
    debate_id: uuid.UUID


class ShareLinks(BaseModel):
    whatsapp: str
    telegram: str
    facebook: str
    x: str
    email: str
    copy_link: str
    qr_code: str


class ConfirmSideRequest(BaseModel):
    side: Side


class LockDebateResponse(BaseModel):
    locked: bool
    status: DebateStatus
    message: str
