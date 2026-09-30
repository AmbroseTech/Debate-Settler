"""Debate schemas: creation, rules, participants, votes, invitations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import DebateMode, DebateStatus, ParticipantRole, Side, VoteChoice

# --- Rules ---


class DebateRulesIn(BaseModel):
    # Local
    required_voters: int = Field(0, ge=0, le=100000)
    votes_public: bool = True
    allow_draw: bool = True
    allow_vote_change: bool = False
    venue: str | None = Field(None, max_length=300)
    city: str | None = Field(None, max_length=120)
    country: str | None = Field(None, max_length=120)
    meeting_link: str | None = Field(None, max_length=500)
    expose_address: bool = False
    # Online
    settlement_source: str | None = Field(None, max_length=300)
    settlement_rule: str | None = None
    event_date: datetime | None = None


class DebateRulesOut(DebateRulesIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


# --- Create / update ---


class DebateCreate(BaseModel):
    mode: DebateMode
    question: str = Field(..., min_length=3, max_length=500)
    side_a_label: str = Field(..., min_length=1, max_length=200)
    side_b_label: str = Field(..., min_length=1, max_length=200)
    category_id: uuid.UUID | None = None
    is_public: bool = True
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str = Field("UTC", max_length=80)
    rules: DebateRulesIn


class DebateParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    role: ParticipantRole
    side: Side | None = None
    confirmed: bool = False
    username: str | None = None


class DebateBrief(BaseModel):
    """Compact representation used in lists / cards (§48)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mode: DebateMode
    status: DebateStatus
    question: str
    side_a_label: str
    side_b_label: str
    timezone: str = "UTC"
    start_at: datetime | None = None
    end_at: datetime | None = None
    views: int = 0
    winner_side: str | None = None
    category_name: str | None = None
    participants_count: int = 0
    votes_count: int = 0
    required_voters: int = 0
    settlement_source: str | None = None
    venue_city: str | None = None


class DebateDetail(DebateBrief):
    is_public: bool
    locked_at: datetime | None = None
    settled_at: datetime | None = None
    result_summary: str | None = None
    shares: int = 0
    comments_count: int = 0
    rules: DebateRulesOut | None = None
    participants: list[DebateParticipantOut] = []
    vote_tally: dict | None = None
    my_side: Side | None = None
    my_role: ParticipantRole | None = None
    has_voted: VoteChoice | None = None


class VoteCounts(BaseModel):
    side_a: int = 0
    side_b: int = 0
    draw: int = 0
    side_a_pct: float = 0.0
    side_b_pct: float = 0.0
    draw_pct: float = 0.0
    total: int = 0
    required: int = 0
    revealed: bool = False


class VoterOut(BaseModel):
    # Participation only — never the side a voter chose (§5.1).
    username: str
    display_name: str | None = None
    avatar_url: str | None = None


class VotersPage(BaseModel):
    total: int
    voters: list[VoterOut] = []
    identities_public: bool = True


class CastVoteRequest(BaseModel):
    choice: VoteChoice


class CastVoteResponse(BaseModel):
    recorded: bool
    message: str
    counts: VoteCounts | None = None


# --- Invitations ---


class CreateInvitationRequest(BaseModel):
    kind: str = Field("voter", pattern="^(voter|opponent)$")
    invited_email: str | None = None
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
    expires_at: datetime | None = None
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


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)
    parent_id: uuid.UUID | None = None


class CommentReactionIn(BaseModel):
    reaction: str = Field(
        ..., pattern="^(like|love|funny|interesting|strong|disagree)$"
    )
