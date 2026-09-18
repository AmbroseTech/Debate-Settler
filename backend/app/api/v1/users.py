"""User profile, preferences and social endpoints (/api/v1/users)."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.models.user import Follow, Profile, User, UserPreferences
from app.schemas.auth import (
    UpdatePreferencesRequest,
    UpdateProfileRequest,
    UserOut,
    UserPreferencesOut,
    UserPublic,
)
from app.schemas.common import Message

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.refresh(user)
    return user


@router.patch("/me/profile", response_model=UserOut)
async def update_profile(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = (await db.execute(select(Profile).where(Profile.user_id == user.id))).scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.avatar_url is not None:
        profile.avatar_url = payload.avatar_url
    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.favorite_categories is not None:
        profile.favorite_categories = ",".join(payload.favorite_categories)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me/preferences", response_model=UserPreferencesOut)
async def get_preferences(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    prefs = (await db.execute(select(UserPreferences).where(UserPreferences.user_id == user.id))).scalar_one_or_none()
    if prefs is None:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


@router.patch("/me/preferences", response_model=UserPreferencesOut)
async def update_preferences(
    payload: UpdatePreferencesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = (await db.execute(select(UserPreferences).where(UserPreferences.user_id == user.id))).scalar_one_or_none()
    if prefs is None:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    await db.commit()
    await db.refresh(prefs)
    return prefs


@router.get("/{user_id}", response_model=UserPublic)
async def get_public_profile(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


@router.post("/{user_id}/follow", response_model=Message)
async def follow(user_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user_id == user.id:
        raise NotFoundError("You can't follow yourself.")
    existing = (
        await db.execute(
            select(Follow).where(Follow.follower_id == user.id, Follow.following_id == user_id)
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(Follow(follower_id=user.id, following_id=user_id))
        await db.commit()
        return Message(message="You are now following this user.")
    return Message(message="Already following.")


@router.post("/{user_id}/unfollow", response_model=Message)
async def unfollow(user_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = (
        await db.execute(
            select(Follow).where(Follow.follower_id == user.id, Follow.following_id == user_id)
        )
    ).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
    return Message(message="Unfollowed.")
