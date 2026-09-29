"""Voting, privacy and 'People Who Voted' tests (§3, §4, §5, §13).

Covers DB-level duplicate-vote protection, server-computed percentages,
the voters list that never exposes choices, closed-debate rejection, and
backend enforcement of private-debate confidentiality.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.models.base import DebateStatus, ParticipantRole, Side, VoteChoice
from app.models.debate import DebateParticipant, DebateVote
from app.core.security import hash_password
from app.models.base import UserRole
from app.models.user import Profile, User, UserPreferences
from tests.conftest import auth_header


def _payload(public=True):
    return {
        "mode": "local",
        "question": "Is pineapple pizza a crime?",
        "side_a_label": "Yes",
        "side_b_label": "No",
        "is_public": public,
        "rules": {"required_voters": 0, "votes_public": True, "allow_draw": True},
    }


async def _lock(client: AsyncClient, db, debate_id: str, headers: dict) -> None:
    opponent = User(
        username="opp_v", email="oppv@example.com",
        hashed_password=hash_password("Password123!"), role=UserRole.user,
    )
    db.add(opponent)
    await db.flush()
    db.add(Profile(user_id=opponent.id))
    db.add(UserPreferences(user_id=opponent.id))
    db.add(DebateParticipant(
        debate_id=uuid.UUID(debate_id), user_id=opponent.id,
        role=ParticipantRole.challenger, side=Side.b, confirmed=True,
    ))
    await db.commit()
    resp = await client.post(f"/api/v1/debates/{debate_id}/lock", headers=headers)
    assert resp.status_code == 200, resp.text


async def _new_user(client: AsyncClient, username: str) -> dict:
    resp = await client.post("/api/v1/auth/register", json={
        "username": username, "email": f"{username}@example.com",
        "password": "Password123!", "confirm_password": "Password123!",
        "accept_terms": True, "country_code": "UG",
    })
    assert resp.status_code == 201, resp.text
    return await auth_header(client, username)


@pytest.mark.asyncio
async def test_duplicate_vote_rejected(client: AsyncClient, seeded_user, db):
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_payload(), headers=headers)).json()
    debate_id = debate["id"]
    await _lock(client, db, debate_id, headers)

    inv = (await client.post(
        f"/api/v1/debates/{debate_id}/invitations",
        json={"kind": "voter", "max_uses": 10, "expires_in_hours": 24}, headers=headers,
    )).json()

    voter = await _new_user(client, "voter1")
    accept = await client.post("/api/v1/debates/invitations/accept", params={"token": inv["token"]}, headers=voter)
    assert accept.status_code == 200, accept.text

    first = await client.post(f"/api/v1/debates/{debate_id}/vote", json={"choice": "side_a"}, headers=voter)
    assert first.status_code == 200, first.text
    dup = await client.post(f"/api/v1/debates/{debate_id}/vote", json={"choice": "side_b"}, headers=voter)
    assert dup.status_code == 409
    counts = (await client.get(f"/api/v1/debates/{debate_id}/votes", headers=voter)).json()
    assert counts["side_a"] == 1 and counts["total"] == 1


@pytest.mark.asyncio
async def test_unique_constraint_blocks_race_at_db_level(client: AsyncClient, seeded_user, db):
    """Even if two requests slip past the app check, the schema rejects the second."""
    headers = await auth_header(client)
    debate_id = uuid.UUID((await client.post("/api/v1/debates", json=_payload(), headers=headers)).json()["id"])
    db.add(DebateVote(debate_id=debate_id, voter_id=seeded_user.id, choice=VoteChoice.side_a, is_valid=True))
    await db.flush()
    with pytest.raises(IntegrityError):
        db.add(DebateVote(debate_id=debate_id, voter_id=seeded_user.id, choice=VoteChoice.side_b, is_valid=True))
        await db.flush()
    await db.rollback()


@pytest.mark.asyncio
async def test_percentages_and_voters_hide_choices(client: AsyncClient, seeded_user, db):
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_payload(), headers=headers)).json()
    debate_id = debate["id"]
    await _lock(client, db, debate_id, headers)
    inv = (await client.post(
        f"/api/v1/debates/{debate_id}/invitations",
        json={"kind": "voter", "max_uses": 10, "expires_in_hours": 24}, headers=headers,
    )).json()

    for i, choice in enumerate(["side_a", "side_a", "side_b"]):
        v = await _new_user(client, f"voter_{i}")
        await client.post("/api/v1/debates/invitations/accept", params={"token": inv["token"]}, headers=v)
        r = await client.post(f"/api/v1/debates/{debate_id}/vote", json={"choice": choice}, headers=v)
        assert r.status_code == 200, r.text

    counts = (await client.get(f"/api/v1/debates/{debate_id}/votes", headers=headers)).json()
    assert counts["side_a"] == 2 and counts["side_b"] == 1 and counts["total"] == 3
    assert counts["side_a_pct"] == pytest.approx(66.7, abs=0.1)
    assert counts["side_b_pct"] == pytest.approx(33.3, abs=0.1)

    voters = (await client.get(f"/api/v1/debates/{debate_id}/voters", headers=headers)).json()
    assert voters["total"] == 3
    assert voters["identities_public"] is True
    names = {x["username"] for x in voters["voters"]}
    assert {"voter_0", "voter_1", "voter_2"} <= names
    # No voter's chosen side is ever exposed.
    for x in voters["voters"]:
        assert "choice" not in x and "side" not in x


@pytest.mark.asyncio
async def test_closed_debate_rejects_votes(client: AsyncClient, seeded_user, db):
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_payload(), headers=headers)).json()
    debate_id = debate["id"]
    await _lock(client, db, debate_id, headers)
    inv = (await client.post(
        f"/api/v1/debates/{debate_id}/invitations",
        json={"kind": "voter", "max_uses": 10, "expires_in_hours": 24}, headers=headers,
    )).json()
    voter = await _new_user(client, "closer")
    await client.post("/api/v1/debates/invitations/accept", params={"token": inv["token"]}, headers=voter)

    # Close the debate from the server side.
    from app.models.debate import Debate
    d = await db.get(Debate, uuid.UUID(debate_id))
    d.status = DebateStatus.closed
    await db.commit()

    resp = await client.post(f"/api/v1/debates/{debate_id}/vote", json={"choice": "side_a"}, headers=voter)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_private_debate_confidential(client: AsyncClient, seeded_user, db):
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_payload(public=False), headers=headers)).json()
    debate_id = debate["id"]

    # Not discoverable in public listing.
    listed = (await client.get("/api/v1/debates")).json()
    assert all(item["id"] != debate_id for item in listed["items"])

    # Anonymous read is rejected.
    anon = await client.get(f"/api/v1/debates/{debate_id}")
    assert anon.status_code == 404

    # A stranger (authenticated, not invited) is rejected too.
    stranger = await _new_user(client, "nosy")
    assert (await client.get(f"/api/v1/debates/{debate_id}", headers=stranger)).status_code == 404
    assert (await client.get(f"/api/v1/debates/{debate_id}/votes", headers=stranger)).status_code == 404
    assert (await client.get(f"/api/v1/debates/{debate_id}/voters", headers=stranger)).status_code == 404
    assert (await client.get(f"/api/v1/debates/{debate_id}/comments", headers=stranger)).status_code == 404

    # The creator can still see it.
    assert (await client.get(f"/api/v1/debates/{debate_id}", headers=headers)).status_code == 200
