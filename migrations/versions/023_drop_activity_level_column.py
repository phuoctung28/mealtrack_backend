"""drop_activity_level_column

Revision ID: 023
Revises: 022
Create Date: 2026-02-28

Drop legacy activity_level column — data already migrated to job_type,
training_days_per_week, training_minutes_per_session in migration 021.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '023'
down_revision: Union[str, None] = '022'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('user_profiles', 'activity_level')


def downgrade() -> None:
    op.add_column(
        'user_profiles',
        sa.Column('activity_level', sa.String(30), nullable=False, server_default='sedentary')
    )
