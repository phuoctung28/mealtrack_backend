"""Add emoji column to meal table.

Revision ID: 041
Revises: 040
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '041'
down_revision = '040'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('meal', sa.Column('emoji', sa.String(8), nullable=True))


def downgrade():
    op.drop_column('meal', 'emoji')
