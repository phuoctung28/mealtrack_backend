"""Add weight_entries table for progress tracking.

Revision ID: 057
Revises: 056
Create Date: 2026-05-01

"""

from alembic import op
import sqlalchemy as sa

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weight_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weight_kg", sa.Float, nullable=False),
        sa.Column("recorded_at", sa.DateTime, nullable=False),
        sa.Column(
            "created_at", sa.DateTime, server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "recorded_at", name="uq_user_recorded_at"),
    )
    op.create_index(
        "idx_weight_entries_user_recorded",
        "weight_entries",
        ["user_id", "recorded_at"],
    )
    op.create_index("idx_weight_entries_user_id", "weight_entries", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_weight_entries_user_id", table_name="weight_entries")
    op.drop_index("idx_weight_entries_user_recorded", table_name="weight_entries")
    op.drop_table("weight_entries")
