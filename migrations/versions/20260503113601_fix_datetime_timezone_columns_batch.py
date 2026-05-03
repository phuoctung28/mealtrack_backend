"""Fix all remaining datetime columns to use TIMESTAMPTZ.

Standardizes all datetime columns to TIMESTAMP WITH TIME ZONE for consistency
with utc_now() which returns timezone-aware datetimes.

Tables affected:
- cheat_days.marked_at
- weight_entries.recorded_at
- feature_flags.created_at, updated_at
- saved_suggestions.saved_at, created_at
- food_reference.created_at, updated_at
- user_profiles.goal_started_at

Revision ID: 059
Revises: 058
Create Date: 2026-05-03 11:36:01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '059'
down_revision: Union[str, None] = '058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS_TO_FIX = [
    ('cheat_days', 'marked_at', False),
    ('weight_entries', 'recorded_at', False),
    ('feature_flags', 'created_at', False),
    ('feature_flags', 'updated_at', False),
    ('saved_suggestions', 'saved_at', False),
    ('saved_suggestions', 'created_at', False),
    # barcode_products was renamed to food_reference in migration 035
    ('food_reference', 'created_at', True),
    ('food_reference', 'updated_at', True),
    ('user_profiles', 'goal_started_at', True),
]


def upgrade() -> None:
    for table, column, nullable in COLUMNS_TO_FIX:
        op.alter_column(
            table, column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(timezone=False),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for table, column, nullable in COLUMNS_TO_FIX:
        op.alter_column(
            table, column,
            type_=sa.DateTime(timezone=False),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
