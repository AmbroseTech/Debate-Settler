"""Security primitives: password hashing, JWT tokens, secure tokens, RBAC.

Passwords are hashed with bcrypt and never stored or returned in plain text.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
import jwt

from app.core.config import settings


# --- Passwords -------------------------------------------------------------
# bcrypt only considers the first 72 bytes of the input; encode and truncate
# explicitly so longer passwords never raise. Hashing is done with bcrypt
# directly (no passlib) to avoid version-detection fragility.

def _pw_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT -------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, extra: Optional[Dict[str, Any]] = None) -> str:
    expire = _now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: Dict[str, Any] = {"sub": subject, "exp": expire, "iat": _now(), "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "iat": _now(), "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# --- Opaque secure tokens (invitations, reset, verification) ---------------

def generate_token_urlsafe(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def generate_reference(prefix: str) -> str:
    """Human-friendly reference such as DS-WD-829173."""
    return f"{prefix}-{secrets.randbelow(900000) + 100000}"


# --- Roles -----------------------------------------------------------------

ROLE_USER = "user"
ROLE_MODERATOR = "moderator"
ROLE_ADMIN = "admin"

ALL_ROLES: List[str] = [ROLE_USER, ROLE_MODERATOR, ROLE_ADMIN]


def role_at_least(role: str, minimum: str) -> bool:
    order = {ROLE_USER: 0, ROLE_MODERATOR: 1, ROLE_ADMIN: 2}
    return order.get(role, 0) >= order.get(minimum, 0)
