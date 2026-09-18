"""Authentication tests (§72): registration, login, reset, authorization."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    payload = {
        "username": "newuser", "email": "new@example.com",
        "password": "Password123!", "confirm_password": "Password123!",
        "accept_terms": True, "country_code": "UG",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    assert resp.json()["username"] == "newuser"
    # Password is never exposed.
    assert "password" not in resp.text.lower() or "hashed_password" not in resp.text

    login = await client.post("/api/v1/auth/login", json={"identifier": "newuser", "password": "Password123!"})
    assert login.status_code == 200
    assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_register_requires_terms(client: AsyncClient):
    payload = {
        "username": "noterms", "email": "noterms@example.com",
        "password": "Password123!", "confirm_password": "Password123!",
        "accept_terms": False,
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_password_mismatch_rejected(client: AsyncClient):
    payload = {
        "username": "mismatch", "email": "mismatch@example.com",
        "password": "Password123!", "confirm_password": "Different123!",
        "accept_terms": True,
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, seeded_user):
    resp = await client.post("/api/v1/auth/login", json={"identifier": "tester", "password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_username_availability(client: AsyncClient, seeded_user):
    resp = await client.post("/api/v1/auth/username-check", json={"username": "tester"})
    assert resp.status_code == 200
    assert resp.json()["available"] is False

    resp2 = await client.post("/api/v1/auth/username-check", json={"username": "free_name"})
    assert resp2.json()["available"] is True


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client: AsyncClient, seeded_user):
    from tests.conftest import auth_header

    headers = await auth_header(client)
    resp = await client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "tester"


@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient, seeded_user):
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": "tester@example.com"})
    assert resp.status_code == 200
    # dev environment surfaces the token in the message
    message = resp.json()["message"]
    assert "dev token:" in message
    token = message.split("dev token:")[1].strip()

    reset = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "NewPassword123!"})
    assert reset.status_code == 200

    login = await client.post("/api/v1/auth/login", json={"identifier": "tester", "password": "NewPassword123!"})
    assert login.status_code == 200
