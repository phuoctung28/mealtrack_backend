"""add_user_timezone

Revision ID: 010
Revises: 009
Create Date: 2025-12-07 23:05:14.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add timezone column to users table and last_water_reminder_at to notification_preferences."""
    # Add timezone column to users table
    op.add_column(
        'users',
        sa.Column(
            'timezone',
            sa.String(50),
            nullable=False,
            server_default='UTC'
        )
    )
    
    # Add index for query performance
    op.create_index(
        'idx_users_timezone',
        'users',
        ['timezone']
    )
    
    # Add last_water_reminder_at to notification_preferences table
    # Use timezone=True to store timezone-aware datetimes (required for UTC comparisons)
    op.add_column(
        'notification_preferences',
        sa.Column(
            'last_water_reminder_at',
            sa.DateTime(timezone=True),
            nullable=True
        )
    )


def downgrade() -> None:
    """Remove timezone column and index, remove last_water_reminder_at column."""
    op.drop_column('notification_preferences', 'last_water_reminder_at')
    op.drop_index('idx_users_timezone', table_name='users')
    op.drop_column('users', 'timezone')

