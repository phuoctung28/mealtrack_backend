"""add_job_type_and_training_columns

Revision ID: 021
Revises: 020
Create Date: 2026-02-27

Add job_type, training_days_per_week, training_minutes_per_session columns
and migrate data from legacy activity_level column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '021'
down_revision: Union[str, None] = '020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('job_type', sa.String(30), nullable=False, server_default='desk'))
    op.add_column('user_profiles', sa.Column('training_days_per_week', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('user_profiles', sa.Column('training_minutes_per_session', sa.Integer(), nullable=False, server_default='0'))

    # Migrate legacy activity_level data to new columns
    op.execute("""
        UPDATE user_profiles
        SET
            job_type = CASE
                WHEN activity_level = 'sedentary' THEN 'desk'
                WHEN activity_level = 'light' THEN 'desk'
                WHEN activity_level = 'moderate' THEN 'desk'
                WHEN activity_level = 'active' THEN 'on_feet'
                WHEN activity_level = 'extra' THEN 'on_feet'
                ELSE 'desk'
            END,
            training_days_per_week = CASE
                WHEN activity_level = 'sedentary' THEN 0
                WHEN activity_level = 'light' THEN 2
                WHEN activity_level = 'moderate' THEN 4
                WHEN activity_level = 'active' THEN 5
                WHEN activity_level = 'extra' THEN 6
                ELSE 0
            END,
            training_minutes_per_session = CASE
                WHEN activity_level = 'sedentary' THEN 0
                WHEN activity_level = 'light' THEN 45
                WHEN activity_level = 'moderate' THEN 60
                WHEN activity_level = 'active' THEN 60
                WHEN activity_level = 'extra' THEN 90
                ELSE 0
            END
    """)


def downgrade() -> None:
    op.drop_column('user_profiles', 'training_minutes_per_session')
    op.drop_column('user_profiles', 'training_days_per_week')
    op.drop_column('user_profiles', 'job_type')
