"""Add disliked_foods column to user_profiles.

Supports the food preference management feature (NM-63).
Stored as JSON array of food names the user wants to avoid (soft exclusion).

Revision ID: 046
Revises: 045
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '046'
down_revision = '045'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'user_profiles',
        sa.Column('disliked_foods', sa.JSON(), nullable=False, server_default='[]'),
    )


def downgrade() -> None:
    op.drop_column('user_profiles', 'disliked_foods')
