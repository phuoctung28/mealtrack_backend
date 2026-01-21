"""add_daily_summary_time_minutes

Revision ID: 014
Revises: 013
Create Date: 2026-01-14 13:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add daily_summary_time_minutes column with server default (9PM = 1260 minutes from midnight)
    # Using server_default handles existing rows automatically without slow UPDATE
    op.add_column('notification_preferences',
        sa.Column('daily_summary_time_minutes', sa.Integer(), nullable=False, server_default='1260')
    )
    # Add constraint to ensure value is between 0 and 1439 (minutes from midnight)
    op.create_check_constraint(
        'check_daily_summary_time',
        'notification_preferences',
        'daily_summary_time_minutes >= 0 AND daily_summary_time_minutes < 1440'
    )


def downgrade() -> None:
    # Drop the daily_summary_time_minutes column
    op.drop_column('notification_preferences', 'daily_summary_time_minutes')
