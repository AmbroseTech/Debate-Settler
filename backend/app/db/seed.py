"""Database bootstrap and seed data (§92).

Creates all tables (or use Alembic in production) and populates realistic
development/demo data: categories, sample users, local + online debates, demo
transactions and notifications. All demo money is clearly labelled DEMO FUNDS.

Run with:  python -m app.db.seed
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import hash_password
from app.models import (
    Category,
    DEFAULT_CATEGORIES,
    Debate,
    DebateParticipant,
    DebateRules,
    Profile,
    User,
    UserPreferences,
    UserRole,
)
from app.models.base import DebateMode, DebateStatus, ParticipantRole, Side
from app.services import ledger_service, notification_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_categories(db) -> None:
    existing = (await db.execute(select(Category))).scalars().all()
    if existing:
        return
    for i, name in enumerate(DEFAULT_CATEGORIES):
        db.add(Category(name=name, slug=name.lower().replace(" ", "-"), sort_order=i))
    await db.flush()


async def seed_users(db) -> list[User]:
    existing = (await db.execute(select(User).where(User.username == "ambrose"))).scalar_one_or_none()
    if existing:
        return [existing]
    users = []
    specs = [
        ("ambrose", "ambrose@debate-settler.local", UserRole.admin),
        ("grace", "grace@example.com", UserRole.user),
        ("ivan", "ivan@example.com", UserRole.moderator),
    ]
    for username, email, role in specs:
        user = User(
            username=username, email=email, hashed_password=hash_password("Password123!"),
            role=role, email_verified=True, country_code="UG",
            terms_accepted_at=_now(),
        )
        db.add(user)
        await db.flush()
        db.add(Profile(user_id=user.id, display_name=username.title()))
        db.add(UserPreferences(user_id=user.id))
        users.append(user)
    await db.flush()
    return users


async def seed_wallets(db, users: list[User]) -> None:
    for user in users:
        wallet = await ledger_service.get_or_create_wallet(db, user.id, "UGX")
        # Demo funds so the financial flow can be exercised.
        await ledger_service.credit_available(
            db, wallet, Decimal("50000.00"),
            description="DEMO FUNDS — seed balance", is_demo=True,
        )


async def seed_debates(db, users: list[User]) -> None:
    existing = (await db.execute(select(Debate))).scalars().first()
    if existing:
        return
    ambrose, grace = users[0], users[1]

    sports = (await db.execute(select(Category).where(Category.name == "Sports"))).scalar_one_or_none()
    tech = (await db.execute(select(Category).where(Category.name == "Technology"))).scalar_one_or_none()

    # Online result debate
    online = Debate(
        creator_id=ambrose.id, category_id=sports.id if sports else None,
        mode=DebateMode.online, status=DebateStatus.open,
        question="Manchester United will beat Arsenal in the next match",
        side_a_label="YES", side_b_label="NO", is_public=True,
        start_at=_now(), end_at=_now() + timedelta(days=1),
        stake_amount=Decimal("3000.00"), currency="UGX",
        platform_fee_percent=Decimal("5.00"), views=120, shares=8,
    )
    db.add(online)
    await db.flush()
    db.add(DebateRules(
        debate_id=online.id, settlement_source="Official match result",
        settlement_rule="YES wins if the official result records Manchester United as winner.",
        event_date=_now() + timedelta(days=1),
    ))
    db.add(DebateParticipant(debate_id=online.id, user_id=ambrose.id, role=ParticipantRole.creator, side=Side.a, confirmed=True))

    # Local debate
    local = Debate(
        creator_id=grace.id, category_id=tech.id if tech else None,
        mode=DebateMode.local, status=DebateStatus.voting,
        question="Which presentation was better?",
        side_a_label="Team Alpha", side_b_label="Team Beta", is_public=True,
        start_at=_now() - timedelta(hours=1), end_at=_now() + timedelta(hours=1),
        stake_amount=Decimal("0.00"), currency="UGX",
        platform_fee_percent=Decimal("5.00"), views=45, shares=3,
    )
    db.add(local)
    await db.flush()
    db.add(DebateRules(
        debate_id=local.id, required_voters=30, votes_public=False, allow_draw=True,
        venue="Bushenyi Community Hall", city="Bushenyi", country="Uganda",
    ))
    db.add(DebateParticipant(debate_id=local.id, user_id=grace.id, role=ParticipantRole.creator, side=Side.a, confirmed=True))

    await db.flush()

    for user in users:
        await notification_service.notify(
            db, user.id, "Welcome to Debate_Settler 👋",
            "Explore trending debates or create your own to settle an argument.",
            category="onboarding",
        )


async def run_seed() -> None:
    if settings.APP_ENV == "production":
        raise RuntimeError("Demo seed data is disabled in production.")
    await create_all()
    async with AsyncSessionLocal() as db:
        await seed_categories(db)
        await db.commit()
        users = await seed_users(db)
        await db.commit()
        await seed_wallets(db, users)
        await db.commit()
        await seed_debates(db, users)
        await db.commit()
    print("Seed complete. Demo login: ambrose / Password123!")


if __name__ == "__main__":
    asyncio.run(run_seed())
