"""add_daily_summary_time_minutes

Revision ID: 014
Revises: 013
Create Date: 2026-01-14 13:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add daily_summary_time_minutes column (9PM = 1260 minutes from midnight)
    # Step 1: Add as nullable with server default (MySQL handles existing rows automatically)
    op.add_column('notification_preferences',
        sa.Column('daily_summary_time_minutes', sa.Integer(), nullable=True, server_default='1260')
    )
    
    # Step 2: Update any NULL values (shouldn't be any, but safety first)
    op.execute(text("UPDATE notification_preferences SET daily_summary_time_minutes = 1260 WHERE daily_summary_time_minutes IS NULL"))
    
    # Step 3: Make column NOT NULL now that all rows have values
    op.alter_column('notification_preferences', 'daily_summary_time_minutes',
        existing_type=sa.Integer(),
        nullable=False,
        server_default='1260'
    )
    
    # Step 4: Add constraint to ensure value is between 0 and 1439 (minutes from midnight)
    # Using raw SQL for MySQL compatibility (MySQL 8.0+ supports CHECK constraints)
    op.execute(text("""
        ALTER TABLE notification_preferences 
        ADD CONSTRAINT check_daily_summary_time 
        CHECK (daily_summary_time_minutes >= 0 AND daily_summary_time_minutes < 1440)
    """))


def downgrade() -> None:
    # Drop the CHECK constraint first (MySQL syntax)
    try:
        op.execute(text("ALTER TABLE notification_preferences DROP CHECK check_daily_summary_time"))
    except Exception:
        # Constraint might not exist, ignore
        pass
    
    # Drop the daily_summary_time_minutes column
    op.drop_column('notification_preferences', 'daily_summary_time_minutes')
