"""Wallet & payment tests (§72): deposit, lock, refund, settlement, withdrawal,
webhook idempotency, insufficient funds."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from app.models.wallet import Wallet
from app.services import ledger_service
from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_wallet_balance_after_seed(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    resp = await client.get("/api/v1/wallet", headers=headers)
    assert resp.status_code == 200
    assert Decimal(resp.json()["available_balance"]) == Decimal("100000.00")


@pytest.mark.asyncio
async def test_demo_deposit_credits_wallet(client: AsyncClient, seeded_user, db):
    headers = await auth_header(client)
    resp = await client.post(
        "/api/v1/deposits",
        json={"provider_code": "demo", "amount": "5000", "destination": "0700000000"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["is_demo"] is True

    wallet_resp = await client.get("/api/v1/wallet", headers=headers)
    assert Decimal(wallet_resp.json()["available_balance"]) == Decimal("105000.00")


@pytest.mark.asyncio
async def test_deposit_idempotency(client: AsyncClient, seeded_user, db):
    headers = await auth_header(client)
    key = str(uuid.uuid4())
    payload = {"provider_code": "demo", "amount": "1000", "idempotency_key": key}
    r1 = await client.post("/api/v1/deposits", json=payload, headers=headers)
    r2 = await client.post("/api/v1/deposits", json=payload, headers=headers)
    assert r1.status_code == 201 and r2.status_code == 201
    # Same idempotency key returns the same deposit — never double credits.
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_lock_and_release_stake(client: AsyncClient, seeded_user, db):
    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == seeded_user.id))).scalar_one()
    debate_id = uuid.uuid4()

    await ledger_service.lock_stake(db, wallet, Decimal("3000.00"), debate_id=debate_id)
    await db.commit()
    assert wallet.available_balance == Decimal("97000.00")
    assert wallet.locked_balance == Decimal("3000.00")

    await ledger_service.release_stake(db, wallet, Decimal("3000.00"), debate_id=debate_id)
    await db.commit()
    assert wallet.available_balance == Decimal("100000.00")
    assert wallet.locked_balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_insufficient_funds(client: AsyncClient, seeded_user, db):
    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == seeded_user.id))).scalar_one()
    from app.core.exceptions import InsufficientFundsError

    with pytest.raises(InsufficientFundsError):
        await ledger_service.lock_stake(db, wallet, Decimal(999999999), debate_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_withdrawal_demo_flow(client: AsyncClient, seeded_user, db):
    headers = await auth_header(client)
    quote = await client.get("/api/v1/withdrawals/quote", params={"amount": "10000"}, headers=headers)
    assert quote.status_code == 200
    assert Decimal(quote.json()["net_amount"]) <= Decimal(10000)

    resp = await client.post(
        "/api/v1/withdrawals",
        json={"provider_code": "demo", "amount": "10000", "destination": "0700000000"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["reference"].startswith("DS-WD")

    wallet_resp = await client.get("/api/v1/wallet", headers=headers)
    # Funds left available balance (reserved/completed).
    assert Decimal(wallet_resp.json()["available_balance"]) < Decimal("100000.00")


@pytest.mark.asyncio
async def test_transaction_history(client: AsyncClient, seeded_user, db):
    headers = await auth_header(client)
    await client.post("/api/v1/deposits", json={"provider_code": "demo", "amount": "2000"}, headers=headers)
    resp = await client.get("/api/v1/wallet/transactions", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_stake_preview_transparency(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    resp = await client.get("/api/v1/wallet/stake-preview", params={"amount": "3000"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["total_pool"]) == Decimal("6000.00")
    assert Decimal(body["platform_fee_amount"]) == Decimal("300.00")
    assert Decimal(body["estimated_winner_settlement"]) == Decimal("5700.00")
    assert body["is_demo"] is True
