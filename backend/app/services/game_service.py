"""Multiplayer game service (§6, §8).

The server owns every game state, turn and result — the client can only request
a move; it never decides legality or the winner. Matches run through the
invitation lifecycle: pending -> accepted/declined, with expiry.

Only games with an implemented rule engine are playable through invitations.
Tic-tac-toe is fully server-authoritative; other listed types require a
dedicated engine before they can be challenged.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    AuthorizationError,
    ValidationError,
)
from app.core.security import generate_token_urlsafe
from app.models.base import GameStatus, GameType, UserRole
from app.models.notification import Game, GameInvitation
from app.models.user import User
from app.services import notification_service, ranking_service

PLAYABLE = {GameType.tic_tac_toe}
_WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Coerce DB datetimes to UTC-aware; SQLite round-trips them naive."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _require_playable(game_type: GameType) -> None:
    if game_type not in PLAYABLE:
        raise ValidationError(
            "Multiplayer challenges aren't available for this game yet. Tic-tac-toe is ready to play."
        )


def _initial_state(p1: uuid.UUID, p2: Optional[uuid.UUID]) -> str:
    return json.dumps({
        "board": [None] * 9,
        "turn": "x",
        "marks": {"x": str(p1), "o": str(p2) if p2 else None},
    })


def _tic_tac_toe_winner(board: list) -> Optional[str]:
    for a, b, c in _WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


async def create_match(db: AsyncSession, user: User, game_type: GameType) -> Game:
    game = Game(game_type=game_type, status=GameStatus.waiting, player_one_id=user.id)
    db.add(game)
    await db.flush()
    return game


async def invite_url(token: str) -> str:
    return f"{settings.FRONTEND_URL}/games/join/{token}"


async def create_invitation(
    db: AsyncSession, game: Game, from_user: User, to_username: Optional[str] = None,
    expires_hours: int = 72,
) -> GameInvitation:
    _require_playable(game.game_type)
    if game.status != GameStatus.waiting:
        raise ConflictError("This match can no longer be invited to.")

    target: Optional[User] = None
    if to_username:
        target = (
            await db.execute(select(User).where(User.username == to_username))
        ).scalar_one_or_none()
        if target is None:
            raise NotFoundError("No player with that username.")
        if target.id == from_user.id:
            raise ConflictError("You can't challenge yourself.")

    invitation = GameInvitation(
        game_id=game.id,
        token=generate_token_urlsafe(24),
        from_user_id=from_user.id,
        to_username=target.username if target else None,
        status="pending",
        expires_at=_now() + timedelta(hours=expires_hours),
    )
    db.add(invitation)
    await db.flush()

    if target:
        await notification_service.notify(
            db, target.id, "You've been challenged to a game",
            f"{from_user.username} challenged you to a match of {game.game_type.value}.",
            category="game", link=f"/games/join/{invitation.token}",
        )
    return invitation


async def _load_invitation(db: AsyncSession, token: str) -> GameInvitation:
    invitation = (
        await db.execute(select(GameInvitation).where(GameInvitation.token == token))
    ).scalar_one_or_none()
    if invitation is None:
        raise NotFoundError("This challenge link is not valid.")
    return invitation


async def preview_invitation(db: AsyncSession, token: str) -> dict:
    invitation = await _load_invitation(db, token)
    game = await db.get(Game, invitation.game_id)
    inviter = await db.get(User, invitation.from_user_id)
    expired = bool(_aware(invitation.expires_at) and _aware(invitation.expires_at) <= _now())
    return {
        "game_id": str(game.id),
        "game_type": game.game_type.value,
        "status": game.status.value,
        "invitation_status": invitation.status,
        "expired": expired,
        "inviter_username": inviter.username if inviter else "a player",
        "to_username": invitation.to_username,
    }


async def accept_invitation(db: AsyncSession, token: str, user: User) -> Game:
    invitation = await _load_invitation(db, token)
    if invitation.status == "declined" or invitation.status == "cancelled":
        raise ConflictError("This challenge is no longer available.")
    if invitation.expires_at and _aware(invitation.expires_at) <= _now():
        invitation.status = "expired"
        await db.flush()
        raise ConflictError("This challenge has expired.")

    game = await db.get(Game, invitation.game_id)
    if game is None:
        raise NotFoundError("That match no longer exists.")

    # Restriction: an addressed challenge can only be accepted by its recipient.
    if invitation.to_username and invitation.to_username != user.username:
        raise AuthorizationError("This challenge was meant for another player.")
    if user.id == game.player_one_id:
        raise ConflictError("You can't accept your own challenge.")

    # Idempotent: re-accepting (double click / refresh) returns the same match.
    if game.player_two_id == user.id:
        invitation.status = "accepted"
        return game
    if game.player_two_id is not None:
        raise ConflictError("This match already has its second player.")

    game.player_two_id = user.id
    game.status = GameStatus.active
    game.state = _initial_state(game.player_one_id, user.id)
    game.current_turn = game.player_one_id  # X (creator) moves first
    invitation.status = "accepted"
    invitation.responded_at = _now()

    link = f"/games/{game.id}"
    for other in (game.player_one_id, user.id):
        await notification_service.notify(
            db, other, "Your match is ready",
            f"{user.username} accepted your {game.game_type.value} challenge. Make your move!",
            category="game", link=link,
        )
    await db.flush()
    return game


async def decline_invitation(db: AsyncSession, token: str, user: User) -> GameInvitation:
    invitation = await _load_invitation(db, token)
    if invitation.status != "pending":
        raise ConflictError("This challenge has already been answered.")
    if invitation.to_username and invitation.to_username != user.username:
        raise AuthorizationError("This challenge was meant for another player.")

    invitation.status = "declined"
    invitation.responded_at = _now()
    game = await db.get(Game, invitation.game_id)
    if game is not None and game.status == GameStatus.waiting:
        game.status = GameStatus.cancelled

    inviter = await db.get(User, invitation.from_user_id)
    if inviter:
        await notification_service.notify(
            db, inviter.id, "Your challenge was declined",
            f"{user.username} declined your {game.game_type.value if game else 'game'} challenge.",
            category="game", link=f"/games",
        )
    await db.flush()
    return invitation


async def get_match(db: AsyncSession, game_id: uuid.UUID, user: User) -> Game:
    game = await db.get(Game, game_id)
    if game is None:
        raise NotFoundError("Match not found.")
    if user.role not in (UserRole.admin, UserRole.moderator) and user.id not in (
        game.player_one_id, game.player_two_id
    ):
        raise NotFoundError("Match not found.")
    return game


async def match_view(db: AsyncSession, game: Game, viewer: Optional[User]) -> dict:
    board: list = []
    your_mark: Optional[str] = None
    can_play = False
    if game.state:
        state = json.loads(game.state)
        board = state.get("board", [])
        marks = state.get("marks", {})
        if viewer is not None:
            if marks.get("x") == str(viewer.id):
                your_mark = "x"
            elif marks.get("o") == str(viewer.id):
                your_mark = "o"
            can_play = (
                game.status == GameStatus.active
                and game.current_turn is not None
                and game.current_turn == viewer.id
            )
    return {
        "id": game.id,
        "game_type": game.game_type,
        "status": game.status,
        "player_one_id": game.player_one_id,
        "player_two_id": game.player_two_id,
        "current_turn": game.current_turn,
        "winner_id": game.winner_id,
        "board": board,
        "your_mark": your_mark,
        "can_play": can_play,
    }


async def make_move(
    db: AsyncSession, game: Game, user: User, cell: int
) -> tuple[Game, str]:
    _require_playable(game.game_type)
    if game.status != GameStatus.active:
        raise ConflictError("This match isn't accepting moves right now.")
    if user.id not in (game.player_one_id, game.player_two_id):
        raise AuthorizationError("You're not a player in this match.")

    state = json.loads(game.state) if game.state else json.loads(
        _initial_state(game.player_one_id, game.player_two_id)
    )
    mark = state["turn"]
    if state["marks"].get(mark) != str(user.id):
        raise ConflictError("It's not your turn.")
    if not isinstance(cell, int) or cell < 0 or cell > 8:
        raise ValidationError("Pick a square between 1 and 9.")

    board = state["board"]
    if board[cell] is not None:
        raise ConflictError("That square is already taken.")

    board[cell] = mark
    winner_mark = _tic_tac_toe_winner(board)

    if winner_mark:
        game.status = GameStatus.finished
        game.winner_id = uuid.UUID(state["marks"][winner_mark])
        game.current_turn = None
        game.state = json.dumps(state)
        await ranking_service.apply_result(db, game)
        await _notify_result(db, game)
        return game, "You won the match!"

    if all(c is not None for c in board):
        game.status = GameStatus.finished
        game.winner_id = None  # draw
        game.current_turn = None
        game.state = json.dumps(state)
        await ranking_service.apply_result(db, game)
        await _notify_result(db, game)
        return game, "The match ended in a draw."

    state["turn"] = "o" if mark == "x" else "x"
    game.current_turn = uuid.UUID(state["marks"][state["turn"]])
    game.state = json.dumps(state)
    await db.flush()
    return game, "Move recorded."


async def _notify_result(db: AsyncSession, game: Game) -> None:
    for pid in (game.player_one_id, game.player_two_id):
        if game.winner_id is None:
            title, body = "Match finished — it's a draw", "Your game ended in a draw."
        elif pid == game.winner_id:
            title, body = "You won the match!", "Well played — your rating has been updated."
        else:
            title, body = "Match finished", "Thanks for playing. Your rating has been updated."
        await notification_service.notify(
            db, pid, title, body, category="game", link=f"/games/{game.id}",
        )
