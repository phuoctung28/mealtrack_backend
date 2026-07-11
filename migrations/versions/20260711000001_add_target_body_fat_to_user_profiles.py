"""Add target body-fat percentage to user profiles.

Revision ID: 20260711000001
Revises: 20260702000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260711000001"
down_revision = "20260702000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("target_body_fat_percentage", sa.Float(), nullable=True),
    )
    op.create_check_constraint(
        "check_target_body_fat_range",
        "user_profiles",
        "target_body_fat_percentage IS NULL OR "
        "(target_body_fat_percentage >= 5 AND target_body_fat_percentage <= 55)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "check_target_body_fat_range",
        "user_profiles",
        type_="check",
    )
    op.drop_column("user_profiles", "target_body_fat_percentage")
