"""Add daily_water_goal_ml to user_profiles.

Revision ID: 20260522100001
Revises: 20260522100000
"""
import sqlalchemy as sa
from alembic import op

revision = "20260522100001"
down_revision = "20260522100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("daily_water_goal_ml", sa.Integer, nullable=True),
    )
    op.create_check_constraint(
        "check_water_goal_positive",
        "user_profiles",
        "daily_water_goal_ml IS NULL OR daily_water_goal_ml > 0",
    )


def downgrade() -> None:
    op.drop_constraint("check_water_goal_positive", "user_profiles", type_="check")
    op.drop_column("user_profiles", "daily_water_goal_ml")
