"""Add persistent visitor sessions and presence.

Revision ID: 0003_visitor_sessions
Revises: 0002_operator_inbox
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_visitor_sessions"
down_revision: str | None = "0002_operator_inbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "visitor_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_visitor_sessions_token_hash",
        "visitor_sessions",
        ["token_hash"],
        unique=True,
    )
    op.alter_column("conversations", "access_token_hash", nullable=True)
    op.add_column(
        "conversations",
        sa.Column("visitor_session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("visitor_last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_visitor_session",
        "conversations",
        "visitor_sessions",
        ["visitor_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_conversations_visitor_session_id",
        "conversations",
        ["visitor_session_id"],
    )
    op.create_index(
        "ix_conversations_visitor_last_seen_at",
        "conversations",
        ["visitor_last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_visitor_last_seen_at", table_name="conversations")
    op.drop_index("ix_conversations_visitor_session_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_visitor_session", "conversations", type_="foreignkey"
    )
    op.drop_column("conversations", "visitor_last_seen_at")
    op.drop_column("conversations", "visitor_session_id")
    op.alter_column("conversations", "access_token_hash", nullable=False)
    op.drop_index("ix_visitor_sessions_token_hash", table_name="visitor_sessions")
    op.drop_table("visitor_sessions")
