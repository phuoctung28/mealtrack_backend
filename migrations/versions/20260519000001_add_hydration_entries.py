"""Add hydration_entries table.

Revision ID: 20260519000001
Revises: 20260519000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260519000001"
down_revision = "20260519000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hydration_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("drink_type", sa.String(32), nullable=False),
        # Per-entry volume: 1–2000 ml (enforced at application layer)
        sa.Column("volume_ml", sa.Integer, nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Composite index supports per-user chronological queries (user_id, logged_at DESC)
    op.create_index(
        "ix_hydration_entries_user_id_logged_at",
        "hydration_entries",
        ["user_id", "logged_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hydration_entries_user_id_logged_at", table_name="hydration_entries"
    )
    op.drop_table("hydration_entries")
