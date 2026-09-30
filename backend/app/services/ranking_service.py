"""Per-game player rankings (§7).

Ratings are computed with Elo and persisted in the database, so they survive
restarts. A finished match applies its result exactly once — the caller guards
with Game.resulted so duplicate submissions can never award points twice.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import GameStatus
from app.models.notification import Game, GameStanding
from app.models.user import Profile, User

ELO_BASE = 1200
ELO_K = 32


def _expected(rating: int, opponent: int) -> float:
    return 1.0 / (1.0 + 10 ** ((opponent - rating) / 400.0))


async def _get_or_create(
    db: AsyncSession, game_type, user_id: uuid.UUID
) -> GameStanding:
    standing = (
        await db.execute(
            select(GameStanding).where(
                GameStanding.game_type == game_type, GameStanding.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if standing is not None:
        return standing
    try:
        async with db.begin_nested():
            standing = GameStanding(
                game_type=game_type,
                user_id=user_id,
                rating=ELO_BASE,
                matches=0,
                wins=0,
                losses=0,
                draws=0,
                current_streak=0,
                longest_streak=0,
            )
            db.add(standing)
            await db.flush()
    except IntegrityError:
        standing = (
            await db.execute(
                select(GameStanding).where(
                    GameStanding.game_type == game_type, GameStanding.user_id == user_id
                )
            )
        ).scalar_one()
    return standing


def _apply_elo(winner: GameStanding, loser: GameStanding) -> None:
    exp_w = _expected(winner.rating, loser.rating)
    exp_l = _expected(loser.rating, winner.rating)
    winner.rating = round(winner.rating + ELO_K * (1.0 - exp_w))
    loser.rating = round(loser.rating + ELO_K * (0.0 - exp_l))


def _record(winner: GameStanding, loser: GameStanding) -> None:
    for s in (winner, loser):
        s.matches += 1
    winner.wins += 1
    winner.current_streak += 1
    winner.longest_streak = max(winner.longest_streak, winner.current_streak)
    loser.losses += 1
    loser.current_streak = 0


def _record_draw(a: GameStanding, b: GameStanding) -> None:
    for s in (a, b):
        s.matches += 1
        s.draws += 1


async def apply_result(db: AsyncSession, game: Game) -> None:
    """Idempotently fold a finished match into both players' standings.

    Only completed two-player matches count. Cancelled / incomplete games are
    excluded, and Game.resulted guarantees re-runs are a no-op (§7.1).
    """
    if game.resulted or game.status.value != "finished":
        return
    if not game.player_one_id or not game.player_two_id:
        return

    a = await _get_or_create(db, game.game_type, game.player_one_id)
    b = await _get_or_create(db, game.game_type, game.player_two_id)

    if game.winner_id is None:
        _record_draw(a, b)
    elif game.winner_id == a.user_id:
        _apply_elo(a, b)
        _record(a, b)
    else:
        _apply_elo(b, a)
        _record(b, a)

    game.resulted = True
    await db.flush()


async def leaderboard(
    db: AsyncSession, game_type, *, period: str = "all_time", limit: int = 50
) -> list[dict]:
    """Return ranked players. all_time uses persisted Elo standings; weekly /
    monthly recompute from matches finished in the window."""
    if period in ("weekly", "monthly"):
        return await _period_board(db, game_type, period, limit)

    rows = (
        await db.execute(
            select(
                GameStanding, User.username, Profile.display_name, Profile.avatar_url
            )
            .join(User, User.id == GameStanding.user_id)
            .outerjoin(Profile, Profile.user_id == GameStanding.user_id)
            .where(GameStanding.game_type == game_type)
            .order_by(GameStanding.rating.desc(), GameStanding.wins.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "rank": i + 1,
            "username": username,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "matches": st.matches,
            "wins": st.wins,
            "losses": st.losses,
            "draws": st.draws,
            "win_pct": round(st.wins * 100 / st.matches, 1) if st.matches else 0.0,
            "current_streak": st.current_streak,
            "rating": st.rating,
        }
        for i, (st, username, display_name, avatar_url) in enumerate(rows)
    ]


async def _period_board(
    db: AsyncSession, game_type, period: str, limit: int
) -> list[dict]:
    days = 7 if period == "weekly" else 30
    since = datetime.now(timezone.utc) - timedelta(days=days)
    games = (
        (
            await db.execute(
                select(Game).where(
                    Game.game_type == game_type,
                    Game.status == GameStatus.finished,
                    Game.created_at >= since,
                    Game.player_one_id.is_not(None),
                    Game.player_two_id.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )

    agg: dict[uuid.UUID, dict] = {}
    for g in games:
        for pid in (g.player_one_id, g.player_two_id):
            entry = agg.setdefault(
                pid, {"matches": 0, "wins": 0, "losses": 0, "draws": 0}
            )
            entry["matches"] += 1
            if g.winner_id is None:
                entry["draws"] += 1
            elif g.winner_id == pid:
                entry["wins"] += 1
            else:
                entry["losses"] += 1

    ids = list(agg.keys())
    if not ids:
        return []
    users = (
        await db.execute(
            select(User.id, User.username, Profile.display_name, Profile.avatar_url)
            .outerjoin(Profile, Profile.user_id == User.id)
            .where(User.id.in_(ids))
        )
    ).all()
    by_id = {uid: (username, dn, av) for uid, username, dn, av in users}

    ranked = sorted(
        agg.items(),
        key=lambda kv: (
            kv[1]["wins"],
            kv[1]["wins"] - kv[1]["losses"],
            kv[1]["matches"],
        ),
        reverse=True,
    )
    return [
        {
            "rank": i + 1,
            "username": by_id.get(uid, ("unknown", None, None))[0],
            "display_name": by_id.get(uid, ("unknown", None, None))[1],
            "avatar_url": by_id.get(uid, ("unknown", None, None))[2],
            "matches": v["matches"],
            "wins": v["wins"],
            "losses": v["losses"],
            "draws": v["draws"],
            "win_pct": round(v["wins"] * 100 / v["matches"], 1)
            if v["matches"]
            else 0.0,
            "current_streak": 0,
            "rating": None,
        }
        for i, (uid, v) in enumerate(ranked[:limit])
    ]
