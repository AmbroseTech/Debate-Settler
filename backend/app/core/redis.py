"""Redis client for caching, rate limiting and ephemeral data.

Never use Redis as the source of truth for financial balances — PostgreSQL is
authoritative. This module provides a small typed helper API.

Resilience: if Redis is unreachable, the helpers transparently fall back to a
best-effort in-process store so a single-instance deployment (and the test
suite) keeps working. Brute-force protection does not rely on this alone — the
database also tracks failed login attempts and lockout (see auth_service).
"""
from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

import redis.asyncio as redis

from app.core.config import settings

_pool: Optional[redis.Redis] = None

# Best-effort in-process fallback: key -> (value, expires_at_epoch_or_None)
_fallback: Dict[str, Tuple[str, Optional[float]]] = {}


def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


def _is_conn_error(exc: Exception) -> bool:
    return isinstance(exc, (redis.ConnectionError, redis.TimeoutError, ConnectionError, OSError))


def _fb_expired(key: str) -> bool:
    item = _fallback.get(key)
    if item is None:
        return True
    expires_at = item[1]
    if expires_at is not None and time.time() >= expires_at:
        _fallback.pop(key, None)
        return True
    return False


async def incr_rate_limit(key: str, window_seconds: int) -> int:
    """Increment a counter for `key`, setting expiry on first hit.

    Falls back to an in-process counter when Redis is unavailable.
    """
    try:
        client = get_redis()
        current = await client.incr(key)
        if current == 1:
            await client.expire(key, window_seconds)
        return int(current)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        if not _is_conn_error(exc):
            raise
        now = time.time()
        if _fb_expired(key):
            _fallback[key] = ("1", now + window_seconds)
            return 1
        value, expires_at = _fallback[key]
        new = int(value) + 1
        _fallback[key] = (str(new), expires_at)
        return new


async def cache_get(key: str) -> Optional[str]:
    try:
        return await get_redis().get(key)
    except Exception as exc:  # noqa: BLE001
        if not _is_conn_error(exc):
            raise
        if _fb_expired(key):
            return None
        return _fallback[key][0]


async def cache_set(key: str, value: str, ttl_seconds: int = 60) -> None:
    try:
        await get_redis().set(key, value, ex=ttl_seconds)
    except Exception as exc:  # noqa: BLE001
        if not _is_conn_error(exc):
            raise
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        _fallback[key] = (value, expires_at)


async def cache_delete(key: str) -> None:
    try:
        await get_redis().delete(key)
    except Exception as exc:  # noqa: BLE001
        if not _is_conn_error(exc):
            raise
    finally:
        _fallback.pop(key, None)
