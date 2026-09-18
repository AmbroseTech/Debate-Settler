"""Security & settlement tests (§72): unauthorized access, invalid tokens,
privilege escalation, and end-to-end local settlement."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.base import DebateStatus
from app.models.wallet import Wallet
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient):
    resp = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_route_forbidden_for_user(client: AsyncClient, seeded_user):
    headers = await auth_header(client)
    resp = await client.get("/api/v1/admin/stats", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_error_does_not_leak_stacktrace(client: AsyncClient):
    resp = await client.get("/api/v1/debates/{}".format(uuid.uuid4()))
    assert resp.status_code in (401, 404)
    body = resp.json()
    assert "error" in body
    assert "Traceback" not in resp.text


@pytest.mark.asyncio
async def test_local_settlement_pays_winner(client: AsyncClient, seeded_user, db):
    """Full flow: two funded sides, votes, close, settle — winner paid net of fee."""
    from app.core.security import hash_password
    from app.models.base import UserRole
    from app.models.user import Profile, User, UserPreferences
    from app.models.debate import Debate, DebateParticipant, DebateRules, DebateVote
    from app.models.base import DebateMode, ParticipantRole, Side, VoteChoice
    from app.services import ledger_service
    from app.settlements import engine

    # Create opponent user.
    opponent = User(
        username="opponent", email="opp@example.com",
        hashed_password=hash_password("Password123!"), role=UserRole.user, country_code="UG",
    )
    db.add(opponent)
    await db.flush()
    db.add(Profile(user_id=opponent.id))
    db.add(UserPreferences(user_id=opponent.id))
    opp_wallet = await ledger_service.get_or_create_wallet(db, opponent.id, "UGX")
    await ledger_service.credit_available(db, opp_wallet, Decimal("50000.00"), is_demo=True)
    user_wallet = (await db.execute(select(Wallet).where(Wallet.user_id == seeded_user.id))).scalar_one()

    debate = Debate(
        creator_id=seeded_user.id, mode=DebateMode.local, status=DebateStatus.active,
        question="Which is better?", side_a_label="A", side_b_label="B",
        stake_amount=Decimal("3000.00"), currency="UGX", platform_fee_percent=Decimal("5.00"),
        locked_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    db.add(debate)
    await db.flush()
    db.add(DebateRules(debate_id=debate.id, required_voters=3, votes_public=False, allow_draw=True))
    db.add(DebateParticipant(debate_id=debate.id, user_id=seeded_user.id, role=ParticipantRole.creator, side=Side.a, confirmed=True))
    db.add(DebateParticipant(debate_id=debate.id, user_id=opponent.id, role=ParticipantRole.challenger, side=Side.b, confirmed=True))

    # Lock stakes for both sides.
    await ledger_service.lock_stake(db, user_wallet, Decimal("3000.00"), debate_id=debate.id)
    await ledger_service.lock_stake(db, opp_wallet, Decimal("3000.00"), debate_id=debate.id)

    # Three voters choose side A (2) over side B (1).
    for i, choice in enumerate([VoteChoice.side_a, VoteChoice.side_a, VoteChoice.side_b]):
        voter = User(
            username=f"voter{i}", email=f"voter{i}@example.com",
            hashed_password=hash_password("Password123!"), role=UserRole.user,
        )
        db.add(voter)
        await db.flush()
        db.add(DebateVote(debate_id=debate.id, voter_id=voter.id, choice=choice, is_valid=True))
    await db.commit()

    settlement = await engine.settle_local_by_votes(db, debate)
    await db.commit()

    assert debate.winner_side == "a"
    assert settlement.platform_fee == Decimal("300.00")
    # Winner stakes 3000 (locked out of available), then receives the full
    # 5700 pool payout (own 3000 back + loser's 3000 minus the 300 fee).
    # Net available: 100000 - 3000 + 5700 = 102700.
    await db.refresh(user_wallet)
    assert user_wallet.available_balance == Decimal("100000.00") - Decimal("3000.00") + Decimal("5700.00")
    assert user_wallet.locked_balance == Decimal("0.00")
