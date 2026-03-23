"""Add language column to notification_preferences table.

Revision ID: 042
Revises: 041
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '042'
down_revision = '041'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('notification_preferences',
        sa.Column('language', sa.String(5), server_default='en', nullable=False))


def downgrade():
    op.drop_column('notification_preferences', 'language')
