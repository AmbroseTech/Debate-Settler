"""Media uploads: images, videos and profile pictures.

Debate Settler is a social platform — debators can attach images and videos as
arguments or evidence, and every user can have a profile picture. Files are
stored on disk under a configurable root and never accepted blindly: type, size
and ownership are validated at the API layer (see app/api/v1/media.py).
"""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Media(BaseModel):
    __tablename__ = "media"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    debate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("debates.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    # image | video | avatar
    kind: Mapped[str] = mapped_column(
        String(20), default="image", nullable=False, index=True
    )
    # Relative path under the configured media root. Never an absolute path.
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    # ready | processing | failed
    status: Mapped[str] = mapped_column(String(20), default="ready", nullable=False)
    # Private media is only served to the owner and debate participants.
    public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
