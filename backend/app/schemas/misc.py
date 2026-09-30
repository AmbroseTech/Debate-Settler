"""Notification, dispute, category, game and admin schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import DisputeStatus, GameStatus, GameType, NotificationChannel

# --- Notifications ---


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    body: str
    category: str
    channel: NotificationChannel
    link: str | None = None
    read: bool
    created_at: datetime


class CreateNotificationRequest(BaseModel):
    user_id: uuid.UUID
    title: str
    body: str
    category: str = "general"
    link: str | None = None
    channel: NotificationChannel = NotificationChannel.in_app


# --- Disputes ---


class DisputeCreate(BaseModel):
    debate_id: uuid.UUID
    reason: str = Field(..., min_length=5, max_length=2000)
    evidence: str | None = None


class DisputeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    debate_id: uuid.UUID
    raised_by: uuid.UUID
    reason: str
    evidence: str | None = None
    status: DisputeStatus
    resolution_notes: str | None = None
    created_at: datetime


class DisputeResolve(BaseModel):
    status: DisputeStatus
    resolution_notes: str | None = None


# --- Categories ---


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    icon: str | None = None


# --- Games ---


class GameCreate(BaseModel):
    game_type: GameType


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    game_type: GameType
    status: GameStatus
    player_one_id: uuid.UUID | None = None
    player_two_id: uuid.UUID | None = None
    state: str | None = None
    current_turn: uuid.UUID | None = None
    winner_id: uuid.UUID | None = None


class GameMoveRequest(BaseModel):
    move: dict


class ChallengeRequest(BaseModel):
    game_type: GameType
    to_username: str | None = Field(None, max_length=50)


class GameInvitationOut(BaseModel):
    token: str
    game_id: uuid.UUID
    game_type: GameType
    status: str
    to_username: str | None = None
    expires_at: datetime | None = None
    invite_url: str


class GamePreviewOut(BaseModel):
    game_id: str
    game_type: str
    status: str
    invitation_status: str
    expired: bool
    inviter_username: str
    to_username: str | None = None


class MoveRequest(BaseModel):
    cell: int = Field(..., ge=0, le=8)


class MatchStateOut(BaseModel):
    id: uuid.UUID
    game_type: GameType
    status: GameStatus
    player_one_id: uuid.UUID | None = None
    player_two_id: uuid.UUID | None = None
    current_turn: uuid.UUID | None = None
    winner_id: uuid.UUID | None = None
    board: list[str | None] = []
    your_mark: str | None = None
    can_play: bool = False


class MoveResultOut(BaseModel):
    message: str
    match: MatchStateOut


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    matches: int
    wins: int
    losses: int
    draws: int
    win_pct: float
    current_streak: int
    rating: int | None = None


class LeaderboardOut(BaseModel):
    game_type: GameType
    period: str
    entries: list[LeaderboardEntry] = []


# --- Admin ---


class AdminStats(BaseModel):
    users: int
    debates: int
    local_debates: int
    online_debates: int
    votes: int
    open_disputes: int


class SettlementSubmit(BaseModel):
    """Admin/worker submits a verified result for an online debate (§22)."""

    debate_id: uuid.UUID
    winner_side: str = Field(..., pattern="^(a|b|draw)$")
    source_verified: bool = True
    settlement_source: str | None = None
    reason: str | None = None
