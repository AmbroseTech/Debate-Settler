"""Security & result tests: unauthorized access, invalid tokens, privilege
escalation, and end-to-end community-voted result finalization."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.base import DebateStatus
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient):
    resp = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_route_forbidden_for_user(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    resp = await client.get("/api/v1/admin/stats", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_error_does_not_leak_stacktrace(client: AsyncClient):
    resp = await client.get("/api/v1/debates/{}".format(uuid.uuid4()))
    assert resp.status_code in (401, 404)
    body = resp.json()
    assert "error" in body
    assert "Traceback" not in resp.text


@pytest.mark.asyncio
async def test_local_result_declares_winner(client: AsyncClient, seeded_user, db):
    """Full community-voted flow: two sides, votes, close, result — winner declared.

    There is no money involved; the outcome is purely the community's vote.
    """
    from app.core.security import hash_password
    from app.models.base import UserRole
    from app.models.user import Profile, User, UserPreferences
    from app.models.debate import Debate, DebateParticipant, DebateRules, DebateVote
    from app.models.base import DebateMode, ParticipantRole, Side, VoteChoice
    from app.settlements import engine

    opponent = User(
        username="opponent", email="opp@example.com",
        hashed_password=hash_password("Password123!"), role=UserRole.user,
    )
    db.add(opponent)
    await db.flush()
    db.add(Profile(user_id=opponent.id))
    db.add(UserPreferences(user_id=opponent.id))

    debate = Debate(
        creator_id=seeded_user.id, mode=DebateMode.local, status=DebateStatus.active,
        question="Which is better?", side_a_label="A", side_b_label="B",
        locked_at=datetime.now(timezone.utc),
    )
    db.add(debate)
    await db.flush()
    db.add(DebateRules(debate_id=debate.id, required_voters=3, votes_public=True, allow_draw=True))
    db.add(DebateParticipant(debate_id=debate.id, user_id=seeded_user.id, role=ParticipantRole.creator, side=Side.a, confirmed=True))
    db.add(DebateParticipant(debate_id=debate.id, user_id=opponent.id, role=ParticipantRole.challenger, side=Side.b, confirmed=True))

    # Three voters choose side A (2) over side B (1).
    for i, choice in enumerate([VoteChoice.side_a, VoteChoice.side_a, VoteChoice.side_b]):
        voter = User(
            username=f"voter{i}", email=f"voter{i}@example.com",
            hashed_password=hash_password("Password123!"), role=UserRole.user,
        )
        db.add(voter)
        await db.flush()
        db.add(DebateVote(debate_id=debate.id, voter_id=voter.id, choice=choice, is_valid=True))
    await db.commit()

    result = await engine.settle_local_by_votes(db, debate)
    await db.commit()

    assert result.winner_side == "a"
    assert result.status == DebateStatus.settled
    assert result.settled_at is not None


@pytest.mark.asyncio
async def test_local_result_needs_minimum_voters(client: AsyncClient, seeded_user, db):
    """A community-voted debate is not finalized until at least 3 votes exist."""
    from app.models.debate import Debate, DebateRules, DebateVote
    from app.models.base import DebateMode, VoteChoice
    from app.settlements import engine

    debate = Debate(
        creator_id=seeded_user.id, mode=DebateMode.local, status=DebateStatus.active,
        question="Too few votes?", side_a_label="A", side_b_label="B",
        locked_at=datetime.now(timezone.utc),
    )
    db.add(debate)
    await db.flush()
    db.add(DebateRules(debate_id=debate.id, required_voters=3, votes_public=True, allow_draw=True))
    db.add(DebateVote(debate_id=debate.id, voter_id=seeded_user.id, choice=VoteChoice.side_a, is_valid=True))
    await db.commit()

    result = await engine.settle_local_by_votes(db, debate)
    await db.commit()

    assert result.winner_side is None
    assert result.status == DebateStatus.closed
