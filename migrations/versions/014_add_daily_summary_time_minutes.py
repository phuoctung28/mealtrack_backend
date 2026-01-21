"""add_daily_summary_time_minutes

Revision ID: 014
Revises: 013
Create Date: 2026-01-14 13:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add daily_summary_time_minutes column to notification_preferences
    # Check if column already exists (may have been partially created during race condition)
    if not column_exists('notification_preferences', 'daily_summary_time_minutes'):
        op.add_column('notification_preferences',
            sa.Column('daily_summary_time_minutes', sa.Integer(), nullable=True, default=1260)
        )
    
    # Update existing rows to default 9PM (1260 minutes from midnight)
    # Safe to run even if column already existed
    op.execute("UPDATE notification_preferences SET daily_summary_time_minutes = 1260 WHERE daily_summary_time_minutes IS NULL")


def downgrade() -> None:
    # Drop the daily_summary_time_minutes column
    op.drop_column('notification_preferences', 'daily_summary_time_minutes')
