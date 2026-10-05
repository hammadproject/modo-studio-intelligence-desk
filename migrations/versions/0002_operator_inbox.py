"""Add operator inbox and human takeover state.

Revision ID: 0002_operator_inbox
Revises: 0001_phase_one
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_operator_inbox"
down_revision: str | None = "0001_phase_one"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "support_status",
            sa.String(32),
            server_default="ai_active",
            nullable=False,
        ),
    )
    op.add_column(
        "conversations", sa.Column("assigned_admin", sa.String(160), nullable=True)
    )
    op.add_column(
        "conversations",
        sa.Column(
            "admin_read_through_sequence",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("human_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("takeover_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_conversations_support_status", "conversations", ["support_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_support_status", table_name="conversations")
    op.drop_column("conversations", "resolved_at")
    op.drop_column("conversations", "takeover_at")
    op.drop_column("conversations", "human_requested_at")
    op.drop_column("conversations", "admin_read_through_sequence")
    op.drop_column("conversations", "assigned_admin")
    op.drop_column("conversations", "support_status")
