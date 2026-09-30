"""multiplayer games: invitations, standings, result flag

Revision ID: 0002_games
Revises: 0001_initial
Create Date: 2026-09-30

Adds the schema for server-authoritative multiplayer games (§6-§8): a
challenge/invitation table, a per-game player standings table for Elo
leaderboards, and a `resulted` flag so a finished match is applied once.
No monetary columns — this remains a free platform.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_games"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def _base_columns() -> list:
    return [
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column("resulted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "game_invitations",
        *_base_columns(),
        sa.Column(
            "game_id",
            UUID,
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(120), nullable=False),
        sa.Column("from_user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("to_username", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_game_invitations_game_id", "game_invitations", ["game_id"])
    op.create_index(
        "ix_game_invitations_token", "game_invitations", ["token"], unique=True
    )
    op.create_index(
        "ix_game_invitations_from_user_id", "game_invitations", ["from_user_id"]
    )
    op.create_index("ix_game_invitations_status", "game_invitations", ["status"])

    op.create_table(
        "game_standings",
        *_base_columns(),
        sa.Column("game_type", sa.String(20), nullable=False),
        sa.Column(
            "user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("game_type", "user_id", name="uq_standing_game_user"),
    )
    op.create_index("ix_game_standings_game_type", "game_standings", ["game_type"])
    op.create_index("ix_game_standings_user_id", "game_standings", ["user_id"])
    op.create_index("ix_game_standings_rating", "game_standings", ["rating"])


def downgrade() -> None:
    op.drop_table("game_standings")
    op.drop_table("game_invitations")
    op.drop_column("games", "resulted")
