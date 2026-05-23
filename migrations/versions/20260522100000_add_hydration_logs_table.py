"""Add hydration_logs table.

Revision ID: 20260522100000
Revises: 20260515000000
"""
import sqlalchemy as sa
from alembic import op

revision = "20260522100000"
down_revision = "20260515000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hydration_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("drink_id", sa.String(50), nullable=False),
        sa.Column("volume_ml", sa.Integer, nullable=False),
        sa.Column("credited_ml", sa.Integer, nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("meal_id", sa.String(36), sa.ForeignKey("meal.meal_id", ondelete="SET NULL"), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_hydration_logs_user_logged", "hydration_logs", ["user_id", "logged_at"])
    op.create_index("ix_hydration_logs_user_id", "hydration_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_hydration_logs_user_id", table_name="hydration_logs")
    op.drop_index("idx_hydration_logs_user_logged", table_name="hydration_logs")
    op.drop_table("hydration_logs")
