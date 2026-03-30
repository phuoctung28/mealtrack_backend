"""Add challenge_duration and training_types columns to user_profiles.

New onboarding redesign fields (NM-44): challenge duration selection
and training type preferences.

Revision ID: 045
Revises: 044
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '045'
down_revision = '044'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('challenge_duration', sa.String(30), nullable=True))
    op.add_column('user_profiles', sa.Column('training_types', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'training_types')
    op.drop_column('user_profiles', 'challenge_duration')
