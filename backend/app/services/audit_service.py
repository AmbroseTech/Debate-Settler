"""Tamper-evident audit logging (§44).

Each entry stores a hash of its own contents chained to the previous entry's
hash, so any retro-active modification breaks the chain and is detectable.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import AuditLog


def _compute_hash(payload: str, previous_hash: str | None) -> str:
    data = f"{previous_hash or ''}|{payload}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


async def record_audit(
    db: AsyncSession,
    action: str,
    *,
    actor_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(1)
    )
    last = result.scalar_one_or_none()
    previous_hash = last.entry_hash if last else None

    details_json = json.dumps(details, default=str) if details else None
    canonical = json.dumps(
        {
            "action": action,
            "actor_id": str(actor_id) if actor_id else None,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details_json,
        },
        sort_keys=True,
    )
    entry_hash = _compute_hash(canonical, previous_hash)

    log = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        details=details_json,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
    )
    db.add(log)
    await db.flush()
    return log
