"""Media endpoints: upload images/videos/avatars, serve and delete them.

All uploads require authentication. Type, size and integrity are validated by the
media service. Private media is only served to its owner or the participants of
the debate it belongs to.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_user
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.debate import Debate, DebateParticipant
from app.models.media import Media
from app.models.user import Profile, User
from app.schemas.common import Message
from app.schemas.media import MediaOut
from app.services import media_service

router = APIRouter(prefix="/media", tags=["media"])


def _media_url(media_id: uuid.UUID) -> str:
    return f"{settings.API_V1_PREFIX}/media/{media_id}"


def _to_out(media: Media) -> MediaOut:
    return MediaOut(
        id=media.id,
        kind=media.kind,
        url=_media_url(media.id),
        original_filename=media.original_filename,
        content_type=media.content_type,
        size_bytes=media.size_bytes,
        width=media.width,
        height=media.height,
        duration_seconds=media.duration_seconds,
        debate_id=media.debate_id,
        public=media.public,
        created_at=media.created_at,
    )


async def _can_access(db: AsyncSession, media: Media, user: User | None) -> bool:
    if media.public:
        return True
    if user is None:
        return False
    if media.owner_id == user.id:
        return True
    if media.debate_id:
        participant = (
            await db.execute(
                select(DebateParticipant).where(
                    DebateParticipant.debate_id == media.debate_id,
                    DebateParticipant.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if participant is not None:
            return True
        debate = await db.get(Debate, media.debate_id)
        if debate is not None and debate.creator_id == user.id:
            return True
    return False


@router.post("/upload", response_model=MediaOut, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    kind: str = Form("image"),
    debate_id: uuid.UUID | None = Form(None),
    public: bool = Form(True),
    duration_seconds: float | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload an image or video, optionally attached to a debate."""
    if kind not in ("image", "video"):
        from app.core.exceptions import ValidationError

        raise ValidationError("Upload kind must be 'image' or 'video'.")

    is_public = public
    if debate_id is not None:
        debate = await db.get(Debate, debate_id)
        if debate is None:
            raise NotFoundError("Debate not found.")
        # Private debates keep their media private regardless of the request.
        is_public = public and debate.is_public

    meta = await media_service.save_upload(
        file,
        kind=kind,
        owner_id=user.id,
        debate_id=debate_id,
        public=is_public,
        duration_seconds=duration_seconds,
    )
    media = Media(**meta)
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return _to_out(media)


@router.post("/avatar", response_model=MediaOut, status_code=201)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload (or replace) the caller's profile picture."""
    meta = await media_service.save_upload(
        file, kind="avatar", owner_id=user.id, public=True
    )
    media = Media(**meta)
    db.add(media)

    profile = (
        await db.execute(select(Profile).where(Profile.user_id == user.id))
    ).scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
    await db.flush()
    profile.avatar_url = _media_url(media.id)
    await db.commit()
    await db.refresh(media)
    return _to_out(media)


@router.get("/{media_id}")
async def get_media(
    media_id: uuid.UUID,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    media = await db.get(Media, media_id)
    if media is None:
        raise NotFoundError("Media not found.")
    if not await _can_access(db, media, user):
        # Do not reveal existence of media the caller may not access.
        raise NotFoundError("Media not found.")
    path = media_service.absolute_path(media.file_path)
    return FileResponse(path, media_type=media.content_type)


@router.delete("/{media_id}", response_model=Message)
async def delete_media(
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    media = await db.get(Media, media_id)
    if media is None:
        raise NotFoundError("Media not found.")
    if media.owner_id != user.id and user.role.value not in ("moderator", "admin"):
        raise AuthorizationError("You can only remove your own uploads.")
    try:
        import os

        os.remove(media_service.absolute_path(media.file_path))
    except OSError:
        pass
    if media.kind == "avatar":
        profile = (
            await db.execute(select(Profile).where(Profile.user_id == user.id))
        ).scalar_one_or_none()
        if profile is not None and profile.avatar_url == _media_url(media.id):
            profile.avatar_url = None
    await db.delete(media)
    await db.commit()
    return Message(message="Media removed.")
