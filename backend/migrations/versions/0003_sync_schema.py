from alembic import op

revision = "0003_sync_schema"
down_revision = "0002_games"
branch_labels = None
depends_on = None

STMTS = [
    "ALTER TABLE debates ADD COLUMN IF NOT EXISTS timezone VARCHAR(80) NOT NULL DEFAULT 'UTC'",
    "ALTER TABLE debates ALTER COLUMN timezone TYPE VARCHAR(80)",
    "ALTER TABLE debate_invitations ADD COLUMN IF NOT EXISTS response VARCHAR(20)",
    "ALTER TABLE debate_participants ADD COLUMN IF NOT EXISTS rules_agreed_at TIMESTAMPTZ",
    """CREATE TABLE IF NOT EXISTS debate_comments (
 id UUID PRIMARY KEY,
 debate_id UUID NOT NULL REFERENCES debates(id),
 user_id UUID NOT NULL REFERENCES users(id),
 parent_id UUID REFERENCES debate_comments(id),
 body TEXT NOT NULL,
 pinned BOOLEAN NOT NULL DEFAULT false,
 hidden BOOLEAN NOT NULL DEFAULT false,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    "CREATE INDEX IF NOT EXISTS ix_debate_comments_debate_id ON debate_comments(debate_id)",
    "CREATE INDEX IF NOT EXISTS ix_debate_comments_user_id ON debate_comments(user_id)",
    """CREATE TABLE IF NOT EXISTS media (
 id UUID PRIMARY KEY,
 owner_id UUID NOT NULL REFERENCES users(id),
 debate_id UUID REFERENCES debates(id),
 kind VARCHAR(20) NOT NULL DEFAULT 'image',
 file_path VARCHAR(500) NOT NULL,
 original_filename VARCHAR(255) NOT NULL,
 content_type VARCHAR(100) NOT NULL,
 size_bytes BIGINT NOT NULL DEFAULT 0,
 width INTEGER, height INTEGER,
 duration_seconds DOUBLE PRECISION,
 status VARCHAR(20) NOT NULL DEFAULT 'ready',
 public BOOLEAN NOT NULL DEFAULT true,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    "CREATE INDEX IF NOT EXISTS ix_media_debate_id ON media(debate_id)",
    "CREATE INDEX IF NOT EXISTS ix_media_kind ON media(kind)",
    "CREATE INDEX IF NOT EXISTS ix_media_owner_id ON media(owner_id)",
    """CREATE TABLE IF NOT EXISTS debate_comment_reactions (
 id UUID PRIMARY KEY,
 comment_id UUID NOT NULL REFERENCES debate_comments(id),
 user_id UUID NOT NULL REFERENCES users(id),
 reaction VARCHAR(20) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    "CREATE INDEX IF NOT EXISTS ix_debate_comment_reactions_comment_id ON debate_comment_reactions(comment_id)",
    "CREATE INDEX IF NOT EXISTS ix_debate_comment_reactions_user_id ON debate_comment_reactions(user_id)",
]


def upgrade():
    for s in STMTS:
        op.execute(s)


def downgrade():
    pass
