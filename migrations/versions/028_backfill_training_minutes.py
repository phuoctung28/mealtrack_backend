"""Backfill training_minutes_per_session for active trainers.

Revision ID: 028
Revises: 027
Create Date: 2026-03-06 13:45:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '028'
down_revision: Union[str, None] = '027'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set reasonable default (30 min) for users who train but have 0 minutes."""
    op.execute("""
        UPDATE user_profiles
        SET training_minutes_per_session = 30
        WHERE training_days_per_week > 0
        AND training_minutes_per_session = 0
        AND is_current = 1
    """)


def downgrade() -> None:
    """Non-reversible data fix."""
    pass
