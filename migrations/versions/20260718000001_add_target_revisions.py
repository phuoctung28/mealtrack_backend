"""Add target revision fences to profiles and weekly budgets.

Revision ID: 20260730000002
Revises: 20260730000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260730000002"
down_revision = "20260730000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column(
            "profile_target_revision", sa.Integer(), nullable=False, server_default="1"
        ),
    )
    op.add_column(
        "weekly_macro_budgets",
        sa.Column("target_revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("user_profiles", "profile_target_revision", server_default=None)
    op.alter_column("weekly_macro_budgets", "target_revision", server_default=None)


def downgrade() -> None:
    op.drop_column("weekly_macro_budgets", "target_revision")
    op.drop_column("user_profiles", "profile_target_revision")
