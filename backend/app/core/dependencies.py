"""Shared FastAPI dependencies: current user, role checks, rate limiting."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    RateLimitedError,
)
from app.core.redis import incr_rate_limit
from app.core.security import decode_token, role_at_least
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthenticationError()
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise AuthenticationError("Your session has expired. Please sign in again.")
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError()
    try:
        user_uuid = uuid.UUID(str(user_id))
    except (ValueError, AttributeError, TypeError):
        raise AuthenticationError("Your session has expired. Please sign in again.")
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise AuthenticationError()
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except AuthenticationError:
        return None


def require_role(minimum: str):
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if not role_at_least(user.role, minimum):
            raise AuthorizationError()
        return user

    return _checker


async def rate_limit(request: Request) -> None:
    """Simple sliding-window rate limit keyed by IP + path."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"ratelimit:{client_ip}:{request.url.path}"
    count = await incr_rate_limit(key, 60)
    if count > settings.RATE_LIMIT_PER_MINUTE:
        raise RateLimitedError()
