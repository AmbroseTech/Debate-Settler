"""Multiplayer games: challenge -> accept -> playable match -> ranked result (§6/§7/§8/§13)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import auth_header


async def _register(client: AsyncClient, username: str, email: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
            "accept_terms": True,
            "country_code": "UG",
        },
    )
    assert resp.status_code == 201, resp.text
    return await auth_header(client, identifier=username, password="Password123!")


def _challenge_body(to_username: str | None = "opponent1"):
    body = {"game_type": "tic_tac_toe"}
    if to_username:
        body["to_username"] = to_username
    return body


async def _play_x_wins(
    client: AsyncClient, game_id: str, headers_x: dict, headers_o: dict
) -> None:
    """X (creator) opens three in a row; O plays the remaining centre/edge squares."""
    # X: 0, O: 3, X: 1, O: 4, X: 2 -> X wins on the top row.
    for cell, headers in [
        (0, headers_x),
        (3, headers_o),
        (1, headers_x),
        (4, headers_o),
        (2, headers_x),
    ]:
        resp = await client.post(
            f"/api/v1/games/{game_id}/move", json={"cell": cell}, headers=headers
        )
        assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_challenge_creates_invitation_link(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    await _register(client, "opponent1", "opp1@example.com")

    resp = await client.post(
        "/api/v1/games/challenge", json=_challenge_body("opponent1"), headers=headers
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["token"]
    assert body["game_type"] == "tic_tac_toe"
    assert body["to_username"] == "opponent1"
    assert body["token"] in body["invite_url"]


@pytest.mark.asyncio
async def test_cannot_challenge_self(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    resp = await client.post(
        "/api/v1/games/challenge", json=_challenge_body("tester"), headers=headers
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_non_playable_game_is_rejected(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    await _register(client, "opponent1", "opp1@example.com")
    resp = await client.post(
        "/api/v1/games/challenge",
        json={"game_type": "chess", "to_username": "opponent1"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_full_match_flow_and_single_ranking_award(
    client: AsyncClient, seeded_user, db
):
    headers_x = await auth_header(client)  # tester, creator / X
    headers_o = await _register(client, "opponent1", "opp1@example.com")

    challenge = (
        await client.post(
            "/api/v1/games/challenge",
            json=_challenge_body("opponent1"),
            headers=headers_x,
        )
    ).json()
    token = challenge["token"]
    game_id = challenge["game_id"]

    # Wrong recipient cannot accept an addressed challenge.
    other = await _register(client, "opponent2", "opp2@example.com")
    wrong = await client.post(
        f"/api/v1/games/invitations/accept?token={token}", headers=other
    )
    assert wrong.status_code == 403

    # The intended recipient accepts, opening a playable match.
    accepted = await client.post(
        f"/api/v1/games/invitations/accept?token={token}", headers=headers_o
    )
    assert accepted.status_code == 200, accepted.text
    match = accepted.json()
    assert match["status"] == "active"
    assert match["your_mark"] == "o"
    assert len(match["board"]) == 9

    # Re-accepting is idempotent — it never spawns a second match.
    again = await client.post(
        f"/api/v1/games/invitations/accept?token={token}", headers=headers_o
    )
    assert again.status_code == 200
    assert again.json()["id"] == game_id

    await _play_x_wins(client, game_id, headers_x, headers_o)

    board = (
        await client.get(
            "/api/v1/games/leaderboard", params={"game_type": "tic_tac_toe"}
        )
    ).json()
    tester = next(e for e in board["entries"] if e["username"] == "tester")
    opp = next(e for e in board["entries"] if e["username"] == "opponent1")
    assert tester["matches"] == 1 and tester["wins"] == 1
    assert opp["matches"] == 1 and opp["losses"] == 1
    assert tester["rating"] > 1200 > opp["rating"]


@pytest.mark.asyncio
async def test_duplicate_result_applies_once(client: AsyncClient, seeded_user, db):
    """Re-running the ranking fold on an already-recorded game awards nothing."""
    from app.models.base import GameType
    from app.models.notification import Game, GameStanding
    from app.services import ranking_service

    headers_x = await auth_header(client)
    headers_o = await _register(client, "opponent1", "opp1@example.com")

    challenge = (
        await client.post(
            "/api/v1/games/challenge",
            json=_challenge_body("opponent1"),
            headers=headers_x,
        )
    ).json()
    game_id = challenge["game_id"]
    await client.post(
        f"/api/v1/games/invitations/accept?token={challenge['token']}",
        headers=headers_o,
    )
    await _play_x_wins(client, game_id, headers_x, headers_o)

    game = await db.get(Game, __import__("uuid").UUID(game_id))
    assert game.resulted is True
    before = (
        (
            await db.execute(
                select(GameStanding).where(
                    GameStanding.game_type == GameType.tic_tac_toe,
                    GameStanding.user_id == game.player_one_id,
                )
            )
        )
        .scalar_one()
        .rating
    )

    # Second application must be a no-op.
    await ranking_service.apply_result(db, game)
    await db.flush()
    after = (
        (
            await db.execute(
                select(GameStanding).where(
                    GameStanding.game_type == GameType.tic_tac_toe,
                    GameStanding.user_id == game.player_one_id,
                )
            )
        )
        .scalar_one()
        .rating
    )
    assert after == before


@pytest.mark.asyncio
async def test_move_out_of_turn_rejected(client: AsyncClient, seeded_user):
    headers_x = await auth_header(client)
    headers_o = await _register(client, "opponent1", "opp1@example.com")
    challenge = (
        await client.post(
            "/api/v1/games/challenge",
            json=_challenge_body("opponent1"),
            headers=headers_x,
        )
    ).json()
    await client.post(
        f"/api/v1/games/invitations/accept?token={challenge['token']}",
        headers=headers_o,
    )
    game_id = challenge["game_id"]
    # O tries to move first (X opens).
    resp = await client.post(
        f"/api/v1/games/{game_id}/move", json={"cell": 0}, headers=headers_o
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_expired_invitation_rejected(client: AsyncClient, seeded_user, db):
    from app.models.notification import GameInvitation

    headers_x = await auth_header(client)
    headers_o = await _register(client, "opponent1", "opp1@example.com")
    challenge = (
        await client.post(
            "/api/v1/games/challenge",
            json=_challenge_body("opponent1"),
            headers=headers_x,
        )
    ).json()

    invitation = (
        await db.execute(
            select(GameInvitation).where(GameInvitation.token == challenge["token"])
        )
    ).scalar_one()
    invitation.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db.commit()

    resp = await client.post(
        f"/api/v1/games/invitations/accept?token={challenge['token']}",
        headers=headers_o,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_stranger_cannot_view_match(client: AsyncClient, seeded_user):
    headers_x = await auth_header(client)
    await _register(client, "opponent1", "opp1@example.com")
    challenge = (
        await client.post(
            "/api/v1/games/challenge",
            json=_challenge_body("opponent1"),
            headers=headers_x,
        )
    ).json()
    stranger = await _register(client, "opponent2", "opp2@example.com")
    resp = await client.get(f"/api/v1/games/{challenge['game_id']}", headers=stranger)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_decline_notifies_and_cancels(client: AsyncClient, seeded_user):
    headers_x = await auth_header(client)
    headers_o = await _register(client, "opponent1", "opp1@example.com")
    challenge = (
        await client.post(
            "/api/v1/games/challenge",
            json=_challenge_body("opponent1"),
            headers=headers_x,
        )
    ).json()

    decline = await client.post(
        f"/api/v1/games/invitations/decline?token={challenge['token']}",
        headers=headers_o,
    )
    assert decline.status_code == 200

    notes = (await client.get("/api/v1/notifications", headers=headers_x)).json()
    assert any("declined" in n["title"].lower() for n in notes)
