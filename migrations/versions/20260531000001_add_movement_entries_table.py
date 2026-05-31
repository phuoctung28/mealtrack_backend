"""Add movement_entries table.

Revision ID: 20260531000001
Revises: 20260525000003
"""

from alembic import op
import sqlalchemy as sa

revision = "20260531000001"
down_revision = "20260525000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movement_entries",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("activity_id", sa.String(64), nullable=True),
        sa.Column("activity_name", sa.String(100), nullable=False),
        sa.Column("duration_min", sa.Integer, nullable=False),
        sa.Column("kcal_burned", sa.Float, nullable=False),
        sa.Column("intensity", sa.String(16), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column(
            "include_in_balance", sa.Boolean, nullable=False, server_default=sa.true()
        ),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
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
    )
    op.create_index("ix_movement_entries_user_id", "movement_entries", ["user_id"])
    op.create_index(
        "ix_movement_entries_activity_id", "movement_entries", ["activity_id"]
    )
    op.create_index(
        "idx_movement_entries_user_logged_at",
        "movement_entries",
        ["user_id", "logged_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_movement_entries_user_logged_at", table_name="movement_entries")
    op.drop_index("ix_movement_entries_activity_id", table_name="movement_entries")
    op.drop_index("ix_movement_entries_user_id", table_name="movement_entries")
    op.drop_table("movement_entries")
