"""Debate tests (§72): create, invite, lock, vote, settlement, rules protection."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import auth_header


def _local_debate_payload():
    return {
        "mode": "local",
        "question": "Which presentation was better?",
        "side_a_label": "Team Alpha",
        "side_b_label": "Team Beta",
        "stake_amount": "0",
        "currency": "UGX",
        "rules": {"required_voters": 3, "votes_public": False, "allow_draw": True},
    }


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
        "stake_amount": "0", "currency": "UGX",
        "rules": {"required_voters": 0},
    }
    resp = await client.post("/api/v1/debates", json=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_real_money_stakes_are_rejected_when_payment_mode_is_demo(client, seeded_user, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "ENABLE_REAL_MONEY", True)
    monkeypatch.setattr(settings, "ENABLE_LOCAL_MONEY", True)
    monkeypatch.setattr(settings, "PAYMENT_MODE", "demo")
    payload = _local_debate_payload()
    payload["stake_amount"] = "1000"
    headers = await auth_header(client)

    resp = await client.post("/api/v1/debates", json=payload, headers=headers)

    assert resp.status_code == 403
    assert "live payments" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_real_money_stakes_wait_for_verified_age_support(client, seeded_user, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "ENABLE_REAL_MONEY", True)
    monkeypatch.setattr(settings, "ENABLE_LOCAL_MONEY", True)
    monkeypatch.setattr(settings, "PAYMENT_MODE", "live")
    monkeypatch.setattr(settings, "REQUIRE_AGE_VERIFICATION", True)
    payload = _local_debate_payload()
    payload["stake_amount"] = "1000"
    headers = await auth_header(client)

    resp = await client.post("/api/v1/debates", json=payload, headers=headers)

    assert resp.status_code == 403
    assert "verified-age records" in resp.json()["error"]["message"]


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
async def test_create_invitation_and_share(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_local_debate_payload(), headers=headers)).json()
    debate_id = debate["id"]

    inv = await client.post(
        f"/api/v1/debates/{debate_id}/invitations",
        json={"kind": "voter", "max_uses": 10, "expires_in_hours": 24},
        headers=headers,
    )
    assert inv.status_code == 200
    assert inv.json()["token"]
    # DB ids are not exposed in the public invite URL.
    assert debate_id not in inv.json()["invite_url"]

    share = await client.get(f"/api/v1/debates/{debate_id}/share", headers=headers)
    assert share.status_code == 200
    assert "whatsapp" in share.json()


@pytest.mark.asyncio
async def test_voting_requires_invitation(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    debate = (await client.post("/api/v1/debates", json=_local_debate_payload(), headers=headers)).json()
    debate_id = debate["id"]
    # The creator is not a registered voter, so voting must be rejected.
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
    # Seed categories directly for this test.
    from app.models.category import Category, DEFAULT_CATEGORIES

    existing = (await client.get("/api/v1/categories")).json()
    if not existing:
        for i, name in enumerate(DEFAULT_CATEGORIES):
            db.add(Category(name=name, slug=name.lower().replace(" ", "-"), sort_order=i))
        await db.commit()
        existing = (await client.get("/api/v1/categories")).json()
    assert len(existing) >= 1
