"""Common model base: UUID primary keys, timestamps, enums shared across models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class BaseModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Abstract base combining UUID pk + timestamps."""

    __abstract__ = True


# --- Enums -----------------------------------------------------------------

class UserRole(str, enum.Enum):
    user = "user"
    moderator = "moderator"
    admin = "admin"


class UserStatus(str, enum.Enum):
    active = "active"
    locked = "locked"
    frozen = "frozen"
    deactivated = "deactivated"


class DebateMode(str, enum.Enum):
    local = "local"
    online = "online"


class DebateStatus(str, enum.Enum):
    draft = "draft"
    open = "open"                       # waiting for opponent
    active = "active"                    # both sides confirmed, funded
    voting = "voting"                    # local: voting window open
    closing_soon = "closing_soon"
    closed = "closed"                    # no more votes / event passed
    being_verified = "being_verified"    # online: awaiting result
    settled = "settled"
    draw = "draw"
    disputed = "disputed"
    funding_timeout = "funding_timeout"
    cancelled = "cancelled"
    under_review = "under_review"
    payment_pending = "payment_pending"


class Side(str, enum.Enum):
    a = "a"
    b = "b"


class ParticipantRole(str, enum.Enum):
    creator = "creator"
    challenger = "challenger"
    voter = "voter"


class VoteChoice(str, enum.Enum):
    side_a = "side_a"
    side_b = "side_b"
    draw = "draw"


class FinancialState(str, enum.Enum):
    pending = "pending"
    authorized = "authorized"
    locked = "locked"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
    reversed = "reversed"
    on_hold = "on_hold"
    under_review = "under_review"
    cancelled = "cancelled"


class TransactionType(str, enum.Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    stake_lock = "stake_lock"
    stake_release = "stake_release"
    payout = "payout"
    refund = "refund"
    platform_fee = "platform_fee"
    provider_fee = "provider_fee"
    tax = "tax"
    reversal = "reversal"
    adjustment = "adjustment"


class WithdrawalStatus(str, enum.Enum):
    requested = "requested"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    under_review = "under_review"


class DepositStatus(str, enum.Enum):
    initiated = "initiated"
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class LedgerAccount(str, enum.Enum):
    user_available = "user_available"
    user_locked = "user_locked"
    user_pending = "user_pending"
    platform_fee_revenue = "platform_fee_revenue"
    provider_fees = "provider_fees"
    escrow = "escrow"


class DisputeStatus(str, enum.Enum):
    open = "open"
    under_review = "under_review"
    resolved = "resolved"
    rejected = "rejected"


class NotificationChannel(str, enum.Enum):
    in_app = "in_app"
    email = "email"
    push = "push"
    sms = "sms"


class GameType(str, enum.Enum):
    chess = "chess"
    checkers = "checkers"
    cards = "cards"
    connect_four = "connect_four"
    tic_tac_toe = "tic_tac_toe"
    reversi = "reversi"


class GameStatus(str, enum.Enum):
    waiting = "waiting"
    active = "active"
    finished = "finished"
    cancelled = "cancelled"
