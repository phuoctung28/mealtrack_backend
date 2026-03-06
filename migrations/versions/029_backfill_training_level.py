"""Backfill training_level for existing users based on training frequency.

Revision ID: 029
Revises: 028
Create Date: 2026-03-06 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '029'
down_revision: Union[str, None] = '028'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Infer training level from training days per week.

    - 0 days: NULL (keep, sedentary)
    - 1-2 days: beginner
    - 3-4 days: intermediate
    - 5-7 days: advanced
    """
    op.execute("""
        UPDATE user_profiles
        SET training_level = CASE
            WHEN training_days_per_week BETWEEN 1 AND 2 THEN 'beginner'
            WHEN training_days_per_week BETWEEN 3 AND 4 THEN 'intermediate'
            WHEN training_days_per_week >= 5 THEN 'advanced'
            ELSE training_level
        END
        WHERE training_level IS NULL
        AND training_days_per_week > 0
        AND is_current = 1
    """)


def downgrade() -> None:
    """Reset inferred values back to NULL."""
    op.execute("""
        UPDATE user_profiles
        SET training_level = NULL
        WHERE training_level IN ('beginner', 'intermediate', 'advanced')
        AND is_current = 1
    """)
