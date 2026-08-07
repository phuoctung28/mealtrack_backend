"""Lower user profile minimum age from 13 to 12 (App Store 12+).

Revision ID: 20260807000001
Revises: 20260806000001
"""

from __future__ import annotations

from alembic import op

revision = "20260807000001"
down_revision = "20260806000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("check_age_range", "user_profiles", type_="check")
    op.create_check_constraint(
        "check_age_range",
        "user_profiles",
        "age >= 12 AND age <= 120",
    )


def downgrade() -> None:
    op.drop_constraint("check_age_range", "user_profiles", type_="check")
    op.create_check_constraint(
        "check_age_range",
        "user_profiles",
        "age >= 13 AND age <= 120",
    )
