"""Add journey progress seed to user profiles.

Revision ID: 20260624000001
Revises: 20260620000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260624000001"
down_revision = "20260620000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column(
            "journey_progress_seed_percent",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.alter_column(
        "user_profiles", "journey_progress_seed_percent", server_default=None
    )
    op.create_check_constraint(
        "check_journey_progress_seed_percent_range",
        "user_profiles",
        "journey_progress_seed_percent >= 0 AND journey_progress_seed_percent <= 100",
    )


def downgrade() -> None:
    op.drop_constraint(
        "check_journey_progress_seed_percent_range",
        "user_profiles",
        type_="check",
    )
    op.drop_column("user_profiles", "journey_progress_seed_percent")
