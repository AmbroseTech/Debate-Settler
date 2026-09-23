"""Games remain free play; real-money games are not implemented."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_game_creation_ignores_client_money_flag(client: AsyncClient, seeded_user):
    headers = await auth_header(client)

    response = await client.post(
        "/api/v1/games",
        json={"game_type": "chess", "is_real_money": True},
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["is_real_money"] is False
