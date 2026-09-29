"""Games are free social play — there is no money anywhere on the platform."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_game_creation_is_free(client: AsyncClient, seeded_user):
    headers = await auth_header(client)

    response = await client.post(
        "/api/v1/games",
        json={"game_type": "chess"},
        headers=headers,
    )

    assert response.status_code == 201, response.text
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
