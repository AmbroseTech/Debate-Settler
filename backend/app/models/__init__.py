"""Model registry — import all models so Alembic metadata is complete."""
from app.models.base import (
    Base,
    BaseModel,
    DebateMode,
    DebateStatus,
    DisputeStatus,
    GameStatus,
    GameType,
    NotificationChannel,
    ParticipantRole,
    Side,
    UserRole,
    UserStatus,
    VoteChoice,
)
from app.models.category import DEFAULT_CATEGORIES, Category
from app.models.debate import (
    Debate,
    DebateEvent,
    DebateInvitation,
    DebateParticipant,
    DebateRules,
    DebateVote,
)
from app.models.notification import AuditLog, Dispute, Game, GameInvitation, GameStanding, Notification
from app.models.user import Follow, Profile, User, UserPreferences, UserSession
from app.models.debate import DebateComment, DebateCommentReaction
from app.models.media import Media

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "Profile",
    "UserPreferences",
    "UserSession",
    "Follow",
    "Category",
    "DEFAULT_CATEGORIES",
    "Debate",
    "DebateRules",
    "DebateParticipant",
    "DebateVote",
    "DebateInvitation",
    "DebateEvent",
    "DebateComment",
    "DebateCommentReaction",
    "Notification",
    "Dispute",
    "AuditLog",
    "Game",
    "GameInvitation",
    "GameStanding",
    "Media",
    # enums
    "UserRole",
    "UserStatus",
    "DebateMode",
    "DebateStatus",
    "Side",
    "ParticipantRole",
    "VoteChoice",
    "DisputeStatus",
    "NotificationChannel",
    "GameType",
    "GameStatus",
]
