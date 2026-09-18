"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-18

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def _base_columns() -> list:
    return [
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        *_base_columns(),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_phone", "users", ["phone"])

    op.create_table(
        "profiles",
        *_base_columns(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("favorite_categories", sa.Text(), nullable=True),
        sa.Column("debates_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("debates_participated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"], unique=True)

    op.create_table(
        "user_preferences",
        *_base_columns(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notify_in_app", sa.Boolean(), server_default=sa.true()),
        sa.Column("notify_email", sa.Boolean(), server_default=sa.true()),
        sa.Column("notify_push", sa.Boolean(), server_default=sa.false()),
        sa.Column("notify_sms", sa.Boolean(), server_default=sa.false()),
        sa.Column("profile_public", sa.Boolean(), server_default=sa.true()),
        sa.Column("allow_invitations", sa.Boolean(), server_default=sa.true()),
        sa.Column("show_tutorial", sa.Boolean(), server_default=sa.true()),
        sa.Column("theme", sa.String(20), server_default="dark"),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"], unique=True)

    op.create_table(
        "user_sessions",
        *_base_columns(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.false()),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

    op.create_table(
        "follows",
        *_base_columns(),
        sa.Column("follower_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("following_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_follows_follower_id", "follows", ["follower_id"])
    op.create_index("ix_follows_following_id", "follows", ["following_id"])

    op.create_table(
        "categories",
        *_base_columns(),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("slug", sa.String(60), nullable=False),
        sa.Column("icon", sa.String(20), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)

    op.create_table(
        "debates",
        *_base_columns(),
        sa.Column("creator_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category_id", UUID, sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("side_a_label", sa.String(200), nullable=False),
        sa.Column("side_b_label", sa.String(200), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stake_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UGX"),
        sa.Column("platform_fee_percent", sa.Numeric(6, 2), nullable=False, server_default="5"),
        sa.Column("winner_side", sa.String(10), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_debates_creator_id", "debates", ["creator_id"])
    op.create_index("ix_debates_category_id", "debates", ["category_id"])
    op.create_index("ix_debates_mode", "debates", ["mode"])
    op.create_index("ix_debates_status", "debates", ["status"])
    op.create_index("ix_debates_end_at", "debates", ["end_at"])

    op.create_table(
        "debate_rules",
        *_base_columns(),
        sa.Column("debate_id", UUID, sa.ForeignKey("debates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("required_voters", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("votes_public", sa.Boolean(), server_default=sa.true()),
        sa.Column("allow_draw", sa.Boolean(), server_default=sa.true()),
        sa.Column("allow_vote_change", sa.Boolean(), server_default=sa.false()),
        sa.Column("draw_returns_stakes", sa.Boolean(), server_default=sa.true()),
        sa.Column("venue", sa.String(300), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("country", sa.String(120), nullable=True),
        sa.Column("meeting_link", sa.String(500), nullable=True),
        sa.Column("expose_address", sa.Boolean(), server_default=sa.false()),
        sa.Column("settlement_source", sa.String(300), nullable=True),
        sa.Column("settlement_rule", sa.Text(), nullable=True),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_debate_rules_debate_id", "debate_rules", ["debate_id"], unique=True)

    op.create_table(
        "debate_participants",
        *_base_columns(),
        sa.Column("debate_id", UUID, sa.ForeignKey("debates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("side", sa.String(5), nullable=True),
        sa.Column("has_funded", sa.Boolean(), server_default=sa.false()),
        sa.Column("confirmed", sa.Boolean(), server_default=sa.false()),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_debate_participants_debate_id", "debate_participants", ["debate_id"])
    op.create_index("ix_debate_participants_user_id", "debate_participants", ["user_id"])

    op.create_table(
        "debate_invitations",
        *_base_columns(),
        sa.Column("debate_id", UUID, sa.ForeignKey("debates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="voter"),
        sa.Column("invited_email", sa.String(255), nullable=True),
        sa.Column("accepted_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used", sa.Boolean(), server_default=sa.false()),
    )
    op.create_index("ix_debate_invitations_token", "debate_invitations", ["token"], unique=True)
    op.create_index("ix_debate_invitations_debate_id", "debate_invitations", ["debate_id"])

    op.create_table(
        "debate_votes",
        *_base_columns(),
        sa.Column("debate_id", UUID, sa.ForeignKey("debates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("voter_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("choice", sa.String(10), nullable=False),
        sa.Column("invitation_id", UUID, sa.ForeignKey("debate_invitations.id"), nullable=True),
        sa.Column("is_valid", sa.Boolean(), server_default=sa.true()),
        sa.Column("changed", sa.Boolean(), server_default=sa.false()),
    )
    op.create_index("ix_debate_votes_debate_id", "debate_votes", ["debate_id"])
    op.create_index("ix_debate_votes_voter_id", "debate_votes", ["voter_id"])
    op.create_unique_constraint("uq_vote_debate_voter", "debate_votes", ["debate_id", "voter_id"])

    op.create_table(
        "debate_events",
        *_base_columns(),
        sa.Column("debate_id", UUID, sa.ForeignKey("debates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("actor_id", UUID, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_debate_events_debate_id", "debate_events", ["debate_id"])

    op.create_table(
        "wallets",
        *_base_columns(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UGX"),
        sa.Column("is_frozen", sa.Boolean(), server_default=sa.false()),
        sa.Column("available_balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("locked_balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("pending_balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
    )
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"], unique=True)

    op.create_table(
        "wallet_accounts",
        *_base_columns(),
        sa.Column("wallet_id", UUID, sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_type", sa.String(30), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
    )
    op.create_index("ix_wallet_accounts_wallet_id", "wallet_accounts", ["wallet_id"])

    op.create_table(
        "payment_transactions",
        *_base_columns(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reference", sa.String(40), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UGX"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(40), nullable=True),
        sa.Column("provider_reference", sa.String(120), nullable=True),
        sa.Column("debate_id", UUID, sa.ForeignKey("debates.id"), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false()),
        sa.Column("idempotency_key", sa.String(120), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
    )
    op.create_index("ix_payment_transactions_reference", "payment_transactions", ["reference"], unique=True)
    op.create_index("ix_payment_transactions_user_id", "payment_transactions", ["user_id"])
    op.create_index("ix_payment_transactions_type", "payment_transactions", ["type"])
    op.create_index("ix_payment_transactions_status", "payment_transactions", ["status"])
    op.create_index("ix_payment_transactions_provider_ref", "payment_transactions", ["provider_reference"])
    op.create_index("ix_payment_transactions_debate_id", "payment_transactions", ["debate_id"])
    op.create_index("ix_payment_transactions_idem", "payment_transactions", ["idempotency_key"], unique=True)

    op.create_table(
        "ledger_entries",
        *_base_columns(),
        sa.Column("transaction_id", UUID, sa.ForeignKey("payment_transactions.id"), nullable=True),
        sa.Column("wallet_id", UUID, sa.ForeignKey("wallets.id"), nullable=True),
        sa.Column("account", sa.String(30), nullable=False),
        sa.Column("entry_type", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UGX"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("debate_id", UUID, sa.ForeignKey("debates.id"), nullable=True),
    )
    op.create_index("ix_ledger_entries_transaction_id", "ledger_entries", ["transaction_id"])
    op.create_index("ix_ledger_entries_wallet_id", "ledger_entries", ["wallet_id"])
    op.create_index("ix_ledger_entries_account", "ledger_entries", ["account"])

    op.create_table(
        "payment_providers",
        *_base_columns(),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("countries", sa.Text(), nullable=True),
        sa.Column("currencies", sa.String(60), nullable=True),
        sa.Column("supports_deposit", sa.Boolean(), server_default=sa.true()),
        sa.Column("supports_payout", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false()),
        sa.Column("config", sa.Text(), nullable=True),
    )
    op.create_index("ix_payment_providers_code", "payment_providers", ["code"], unique=True)

    op.create_table(
        "deposits",
        *_base_columns(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("wallet_id", UUID, sa.ForeignKey("wallets.id"), nullable=False),
        sa.Column("reference", sa.String(40), nullable=False),
        sa.Column("provider_code", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UGX"),
        sa.Column("status", sa.String(20), nullable=False, server_default="initiated"),
        sa.Column("provider_reference", sa.String(120), nullable=True),
        sa.Column("destination_hint", sa.String(120), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false()),
        sa.Column("idempotency_key", sa.String(120), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_deposits_reference", "deposits", ["reference"], unique=True)
    op.create_index("ix_deposits_user_id", "deposits", ["user_id"])
    op.create_index("ix_deposits_wallet_id", "deposits", ["wallet_id"])
    op.create_index("ix_deposits_status", "deposits", ["status"])
    op.create_index("ix_deposits_idem", "deposits", ["idempotency_key"], unique=True)

    op.create_table(
        "withdrawals",
        *_base_columns(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("wallet_id", UUID, sa.ForeignKey("wallets.id"), nullable=False),
        sa.Column("reference", sa.String(40), nullable=False),
        sa.Column("provider_code", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("fee", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UGX"),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("destination_hint", sa.String(120), nullable=True),
        sa.Column("provider_reference", sa.String(120), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false()),
        sa.Column("idempotency_key", sa.String(120), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_withdrawals_reference", "withdrawals", ["reference"], unique=True)
    op.create_index("ix_withdrawals_user_id", "withdrawals", ["user_id"])
    op.create_index("ix_withdrawals_status", "withdrawals", ["status"])
    op.create_index("ix_withdrawals_idem", "withdrawals", ["idempotency_key"], unique=True)

    op.create_table(
        "settlement_records",
        *_base_columns(),
        sa.Column("debate_id", UUID, sa.ForeignKey("debates.id"), nullable=False),
        sa.Column("winner_side", sa.String(10), nullable=True),
        sa.Column("gross_pool", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("platform_fee", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("winner_payout", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UGX"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("source_verified", sa.Boolean(), server_default=sa.false()),
        sa.Column("settlement_source", sa.String(300), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_settlement_records_debate_id", "settlement_records", ["debate_id"], unique=True)
    op.create_index("ix_settlement_records_status", "settlement_records", ["status"])

    op.create_table(
        "notifications",
        *_base_columns(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="in_app"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(40), nullable=False, server_default="general"),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("read", sa.Boolean(), server_default=sa.false()),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_read", "notifications", ["read"])

    op.create_table(
        "disputes",
        *_base_columns(),
        sa.Column("debate_id", UUID, sa.ForeignKey("debates.id"), nullable=False),
        sa.Column("raised_by", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("payout_on_hold", sa.Boolean(), server_default=sa.true()),
        sa.Column("resolved_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_disputes_debate_id", "disputes", ["debate_id"])
    op.create_index("ix_disputes_raised_by", "disputes", ["raised_by"])
    op.create_index("ix_disputes_status", "disputes", ["status"])

    op.create_table(
        "audit_logs",
        *_base_columns(),
        sa.Column("actor_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=True),
        sa.Column("entity_id", sa.String(60), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("previous_hash", sa.String(64), nullable=True),
        sa.Column("entry_hash", sa.String(64), nullable=True),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    op.create_table(
        "games",
        *_base_columns(),
        sa.Column("game_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("player_one_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("player_two_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_real_money", sa.Boolean(), server_default=sa.false()),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("current_turn", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("winner_id", UUID, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_games_game_type", "games", ["game_type"])


def downgrade() -> None:
    for table in [
        "games", "audit_logs", "disputes", "notifications", "settlement_records",
        "withdrawals", "deposits", "payment_providers", "ledger_entries",
        "payment_transactions", "wallet_accounts", "wallets", "debate_events",
        "debate_votes", "debate_invitations", "debate_participants", "debate_rules",
        "debates", "categories", "follows", "user_sessions", "user_preferences",
        "profiles", "users",
    ]:
        op.drop_table(table)
