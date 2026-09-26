<<<<<<< HEAD
"""Games are free social play — there is no money anywhere on the platform."""
=======
"""Games remain free play; real-money games are not implemented."""
>>>>>>> 0e93d668861d343013d6dc8b4026f728e4fb7e75
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


@pytest.mark.asyncio
<<<<<<< HEAD
async def test_game_creation_is_free(client: AsyncClient, seeded_user):
=======
async def test_game_creation_ignores_client_money_flag(client: AsyncClient, seeded_user):
>>>>>>> 0e93d668861d343013d6dc8b4026f728e4fb7e75
    headers = await auth_header(client)

    response = await client.post(
        "/api/v1/games",
<<<<<<< HEAD
        json={"game_type": "chess"},
=======
        json={"game_type": "chess", "is_real_money": True},
>>>>>>> 0e93d668861d343013d6dc8b4026f728e4fb7e75
        headers=headers,
    )

    assert response.status_code == 201, response.text
<<<<<<< HEAD
    body = response.json()
    assert body["game_type"] == "chess"
    assert body["status"] == "waiting"
    # No monetary concept is exposed by the games API.
    assert "is_real_money" not in body


@pytest.mark.asyncio
async def test_game_types_listed(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    response = await client.get("/api/v1/games/types", headers=headers)
    assert response.status_code == 200
    assert "chess" in response.json()
=======
    assert response.json()["is_real_money"] is False
>>>>>>> 0e93d668861d343013d6dc8b4026f728e4fb7e75
