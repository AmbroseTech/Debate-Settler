"""Pytest fixtures: in-memory SQLite DB, async client, seeded users."""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Use SQLite for tests so no external DB is required.
# These must be set BEFORE any `app` module is imported (settings load at import time).
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["PAYMENT_MODE"] = "demo"
os.environ["ENABLE_REAL_MONEY"] = "false"

from app.core.database import Base, engine, get_db
from app.core.security import hash_password
from app.main import app
from app.models.base import UserRole
from app.models.user import Profile, User, UserPreferences
from app.services import ledger_service


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


TestSession = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_user(db: AsyncSession) -> User:
    user = User(
        username="tester",
        email="tester@example.com",
        hashed_password=hash_password("Password123!"),
        role=UserRole.user,
        email_verified=True,
        country_code="UG",
    )
    db.add(user)
    await db.flush()
    db.add(Profile(user_id=user.id, display_name="Tester"))
    db.add(UserPreferences(user_id=user.id))
    wallet = await ledger_service.get_or_create_wallet(db, user.id, "UGX")
    await ledger_service.credit_available(db, wallet, Decimal("100000.00"), is_demo=True)
    await db.commit()
    return user


async def auth_header(
    client: AsyncClient,
    identifier: str = "tester",
    password: str = "Password123!",
) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}