"""Add goal_start_weight_kg and goal_started_at to user_profiles.

Revision ID: 058
Revises: 057
Create Date: 2026-05-01

"""

from alembic import op
import sqlalchemy as sa

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("goal_start_weight_kg", sa.Float, nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("goal_started_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "goal_started_at")
    op.drop_column("user_profiles", "goal_start_weight_kg")
