"""Notification, dispute, category, game and admin schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

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
    link: Optional[str] = None
    read: bool
    created_at: datetime


class CreateNotificationRequest(BaseModel):
    user_id: uuid.UUID
    title: str
    body: str
    category: str = "general"
    link: Optional[str] = None
    channel: NotificationChannel = NotificationChannel.in_app


# --- Disputes ---

class DisputeCreate(BaseModel):
    debate_id: uuid.UUID
    reason: str = Field(..., min_length=5, max_length=2000)
    evidence: Optional[str] = None


class DisputeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    debate_id: uuid.UUID
    raised_by: uuid.UUID
    reason: str
    evidence: Optional[str] = None
    status: DisputeStatus
    payout_on_hold: bool
    resolution_notes: Optional[str] = None
    created_at: datetime


class DisputeResolve(BaseModel):
    status: DisputeStatus
    resolution_notes: Optional[str] = None


# --- Categories ---

class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    icon: Optional[str] = None


# --- Games ---

class GameCreate(BaseModel):
    game_type: GameType


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    game_type: GameType
    status: GameStatus
    player_one_id: Optional[uuid.UUID] = None
    player_two_id: Optional[uuid.UUID] = None
    is_real_money: bool = False
    state: Optional[str] = None
    current_turn: Optional[uuid.UUID] = None
    winner_id: Optional[uuid.UUID] = None


class GameMoveRequest(BaseModel):
    move: dict


# --- Admin ---

class AdminStats(BaseModel):
    users: int
    debates: int
    local_debates: int
    online_debates: int
    votes: int
    deposits: Decimal
    withdrawals: Decimal
    platform_fees: Decimal
    open_disputes: int
    currency: str


class SettlementSubmit(BaseModel):
    """Admin/worker submits a verified result for an online debate (§22)."""

    debate_id: uuid.UUID
    winner_side: str = Field(..., pattern="^(a|b|draw)$")
    source_verified: bool = True
    settlement_source: Optional[str] = None
    reason: Optional[str] = None
