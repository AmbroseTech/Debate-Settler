"""Auth service: registration, login, lockout, verification, reset (§5, §41).

Passwords are hashed and never exposed. Brute-force protection locks an account
after repeated failures. Security events are audited.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.redis import cache_delete, cache_get, cache_set, incr_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_token_urlsafe,
    hash_password,
    verify_password,
)
from app.models.base import UserRole, UserStatus
from app.models.user import Profile, User, UserPreferences
from app.services.audit_service import record_audit
from app.services import notification_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def username_available(db: AsyncSession, username: str) -> bool:
    result = await db.execute(select(User).where(User.username.ilike(username)))
    return result.scalar_one_or_none() is None


async def register(
    db: AsyncSession,
    *,
    username: str,
    email: str,
    password: str,
    confirm_password: str,
    accept_terms: bool,
    phone: Optional[str] = None,
    country_code: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> User:
    if password != confirm_password:
        raise ValidationError("Passwords do not match.")
    if not accept_terms:
        raise ValidationError("You must accept the Terms and Conditions to continue.")

    existing = await db.execute(
        select(User).where(or_(User.username.ilike(username), User.email.ilike(email)))
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("That username or email is already taken.")

    user = User(
        username=username,
        email=email.lower(),
        phone=phone,
        hashed_password=hash_password(password),
        role=UserRole.user,
        status=UserStatus.active,
        country_code=country_code,
        terms_accepted_at=_now(),
    )
    db.add(user)
    await db.flush()
    db.add(Profile(user_id=user.id, display_name=username))
    db.add(UserPreferences(user_id=user.id))
    await record_audit(
        db, "account_creation", actor_id=user.id, entity_type="user",
        entity_id=str(user.id), ip_address=ip_address,
    )
    await notification_service.notify(
        db, user.id, "Welcome to Debate_Settler 👋",
        "Create a debate, join one, or vote in a local debate to get started.",
        category="onboarding",
    )
    await db.flush()
    return user


async def authenticate(
    db: AsyncSession, identifier: str, password: str, *, ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[User, str, str]:
    # Simple per-identifier rate limit to blunt brute-force attempts.
    rl_key = f"login:{identifier.lower()}"
    attempts = await incr_rate_limit(rl_key, 60)
    if attempts > settings.MAX_LOGIN_ATTEMPTS * 2:
        raise AccountLockedError()

    result = await db.execute(
        select(User).where(or_(User.username.ilike(identifier), User.email.ilike(identifier.lower())))
    )
    user = result.scalar_one_or_none()
    if user is None:
        await record_audit(db, "login_failed", entity_type="user", ip_address=ip_address,
                           details={"identifier": identifier, "reason": "unknown_account"})
        raise AuthenticationError("Incorrect username/email or password.")

    if user.is_locked():
        raise AccountLockedError()
    if not user.is_active:
        raise AuthenticationError("This account is deactivated.")

    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.status = UserStatus.locked
            user.locked_until = _now() + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
            user.failed_login_attempts = 0
            await record_audit(db, "account_locked", actor_id=user.id, entity_type="user",
                               entity_id=str(user.id), ip_address=ip_address)
        await record_audit(db, "login_failed", actor_id=user.id, entity_type="user",
                           entity_id=str(user.id), ip_address=ip_address)
        await db.flush()
        raise AuthenticationError("Incorrect username/email or password.")

    # Success — reset counters and clear rate limit.
    user.failed_login_attempts = 0
    user.status = UserStatus.active
    user.locked_until = None
    await cache_delete(rl_key)
    await record_audit(db, "login", actor_id=user.id, entity_type="user",
                       entity_id=str(user.id), ip_address=ip_address)
    await db.flush()

    access = create_access_token(str(user.id), extra={"role": user.role.value})
    refresh = create_refresh_token(str(user.id))
    return user, access, refresh


async def change_password(db: AsyncSession, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.hashed_password):
        raise AuthenticationError("Your current password is incorrect.")
    if len(new) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    user.hashed_password = hash_password(new)
    await record_audit(db, "password_change", actor_id=user.id, entity_type="user", entity_id=str(user.id))
    await db.flush()


async def request_password_reset(db: AsyncSession, email: str) -> str:
    result = await db.execute(select(User).where(User.email.ilike(email.lower())))
    user = result.scalar_one_or_none()
    if user is None:
        # Do not reveal whether the account exists.
        return ""
    token = generate_token_urlsafe(32)
    await cache_set(f"pwd_reset:{token}", str(user.id), ttl_seconds=3600)
    await record_audit(db, "password_reset_requested", actor_id=user.id, entity_type="user", entity_id=str(user.id))
    return token


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    user_id = await cache_get(f"pwd_reset:{token}")
    if not user_id:
        raise ValidationError("This reset link is invalid or has expired.")
    if len(new_password) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    user = await db.get(User, uuid.UUID(user_id))
    if user is None:
        raise NotFoundError("Account not found.")
    user.hashed_password = hash_password(new_password)
    user.status = UserStatus.active
    user.locked_until = None
    user.failed_login_attempts = 0
    await cache_delete(f"pwd_reset:{token}")
    await record_audit(db, "password_reset", actor_id=user.id, entity_type="user", entity_id=str(user.id))
    await db.flush()


async def request_email_verification(db: AsyncSession, user: User) -> str:
    token = generate_token_urlsafe(32)
    await cache_set(f"email_verify:{token}", str(user.id), ttl_seconds=86400)
    return token


async def verify_email(db: AsyncSession, token: str) -> User:
    user_id = await cache_get(f"email_verify:{token}")
    if not user_id:
        raise ValidationError("This verification link is invalid or has expired.")
    user = await db.get(User, uuid.UUID(user_id))
    if user is None:
        raise NotFoundError("Account not found.")
    user.email_verified = True
    await cache_delete(f"email_verify:{token}")
    await record_audit(db, "email_verified", actor_id=user.id, entity_type="user", entity_id=str(user.id))
    await db.flush()
    return user
