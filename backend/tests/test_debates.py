"""Debate tests: create, invite opponent, lock, voter invitations, voting, rules."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.base import ParticipantRole, Side
from app.models.debate import DebateParticipant
from tests.conftest import auth_header


def _local_debate_payload():
    return {
        "mode": "local",
        "question": "Which presentation was better?",
        "side_a_label": "Team Alpha",
        "side_b_label": "Team Beta",
        "rules": {"required_voters": 3, "votes_public": True, "allow_draw": True},
    }


async def _lock_debate(client: AsyncClient, db, debate_id: str, headers: dict) -> None:
    """Add a confirmed opponent on side B and lock the debate (both sides agreed)."""
    from app.core.security import hash_password
    from app.models.base import UserRole
    from app.models.user import Profile, User, UserPreferences

    opponent = User(
        username="opponent", email="opp@example.com",
        hashed_password=hash_password("Password123!"), role=UserRole.user,
    )
    db.add(opponent)
    await db.flush()
    db.add(Profile(user_id=opponent.id))
    db.add(UserPreferences(user_id=opponent.id))
    db.add(DebateParticipant(
        debate_id=__import__("uuid").UUID(debate_id), user_id=opponent.id,
        role=ParticipantRole.challenger, side=Side.b, confirmed=True,
    ))
    await db.commit()
    resp = await client.post(f"/api/v1/debates/{debate_id}/lock", headers=headers)
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_create_local_debate(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    resp = await client.post("/api/v1/debates", json=_local_debate_payload(), headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["mode"] == "local"
    assert body["question"] == "Which presentation was better?"
    assert body["my_role"] == "creator"


@pytest.mark.asyncio
async def test_online_debate_requires_settlement_source(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    payload = {
        "mode": "online",
        "question": "Manchester United will beat Arsenal",
        "side_a_label": "YES", "side_b_label": "NO",
        "rules": {"required_voters": 0},
    }
    resp = await client.post("/api/v1/debates", json=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_and_search_debates(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    await client.post("/api/v1/debates", json=_local_debate_payload(), headers=headers)
    listing = await client.get("/api/v1/debates")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    search = await client.get("/api/v1/debates/search", params={"q": "presentation"})
    assert search.status_code == 200
    assert search.json()["total"] >= 1


@pytest.mark.asyncio
async def test_opponent_invitation_before_lock(client: AsyncClient, seeded_user):
    """An opponent can be invited while the debate is still open (§4/§5)."""
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_local_debate_payload(), headers=headers)).json()
    debate_id = debate["id"]

    inv = await client.post(
        f"/api/v1/debates/{debate_id}/invitations",
        json={"kind": "opponent", "max_uses": 1, "expires_in_hours": 72},
        headers=headers,
    )
    assert inv.status_code == 200, inv.text
    assert inv.json()["token"]
    # DB ids are never exposed in the public invite URL.
    assert debate_id not in inv.json()["invite_url"]


@pytest.mark.asyncio
async def test_voter_invitation_requires_lock(client: AsyncClient, seeded_user):
    """Voter invitations only open after both debators agree and lock (§6)."""
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_local_debate_payload(), headers=headers)).json()
    debate_id = debate["id"]

    inv = await client.post(
        f"/api/v1/debates/{debate_id}/invitations",
        json={"kind": "voter", "max_uses": 10, "expires_in_hours": 24},
        headers=headers,
    )
    assert inv.status_code == 409


@pytest.mark.asyncio
async def test_voter_invitation_and_share_after_lock(client: AsyncClient, seeded_user, db):
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_local_debate_payload(), headers=headers)).json()
    debate_id = debate["id"]
    await _lock_debate(client, db, debate_id, headers)

    inv = await client.post(
        f"/api/v1/debates/{debate_id}/invitations",
        json={"kind": "voter", "max_uses": 10, "expires_in_hours": 24},
        headers=headers,
    )
    assert inv.status_code == 200, inv.text
    assert inv.json()["token"]
    assert debate_id not in inv.json()["invite_url"]

    share = await client.get(f"/api/v1/debates/{debate_id}/share", headers=headers)
    assert share.status_code == 200
    assert "whatsapp" in share.json()


@pytest.mark.asyncio
async def test_voting_requires_invitation(client: AsyncClient, seeded_user, db):
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_local_debate_payload(), headers=headers)).json()
    debate_id = debate["id"]
    await _lock_debate(client, db, debate_id, headers)
    # The creator is a debator, not a registered voter, so voting must be rejected.
    resp = await client.post(
        f"/api/v1/debates/{debate_id}/vote", json={"choice": "side_a"}, headers=headers
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cannot_lock_without_both_sides(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_local_debate_payload(), headers=headers)).json()
    resp = await client.post(f"/api/v1/debates/{debate['id']}/lock", headers=headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_categories_seeded_and_listed(client: AsyncClient, seeded_user, db):
    from app.models.category import Category, DEFAULT_CATEGORIES

    existing = (await client.get("/api/v1/categories")).json()
    if not existing:
        for i, name in enumerate(DEFAULT_CATEGORIES):
            db.add(Category(name=name, slug=name.lower().replace(" ", "-"), sort_order=i))
        await db.commit()
        existing = (await client.get("/api/v1/categories")).json()
    assert len(existing) >= 1
