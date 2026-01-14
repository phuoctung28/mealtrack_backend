"""add_water_reminder_time_minutes

Revision ID: 013
Revises: 012
Create Date: 2026-01-14 12:02:09.583571

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add water_reminder_time_minutes column to notification_preferences
    op.add_column('notification_preferences',
        sa.Column('water_reminder_time_minutes', sa.Integer(), nullable=True, default=960)
    )
    # Update existing rows to default 4PM (960 minutes from midnight)
    op.execute("UPDATE notification_preferences SET water_reminder_time_minutes = 960 WHERE water_reminder_time_minutes IS NULL")


def downgrade() -> None:
    # Drop the water_reminder_time_minutes column
    op.drop_column('notification_preferences', 'water_reminder_time_minutes')
