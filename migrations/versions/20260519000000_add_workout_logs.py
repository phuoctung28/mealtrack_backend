"""Add workout_logs table.

Revision ID: 20260519000000
Revises: 20260515000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260519000000"
down_revision = "20260515000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workout_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("workout_type", sa.String(32), nullable=False),
        sa.Column("intensity", sa.String(16), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("met_value", sa.Numeric(4, 2), nullable=False),
        sa.Column("weight_kg_snapshot", sa.Numeric(5, 2), nullable=True),
        sa.Column("estimated_burn_kcal", sa.Numeric(7, 1), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Composite index supports per-user chronological queries (user_id, logged_at DESC)
    op.create_index(
        "ix_workout_logs_user_id_logged_at",
        "workout_logs",
        ["user_id", "logged_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_workout_logs_user_id_logged_at", table_name="workout_logs")
    op.drop_table("workout_logs")
