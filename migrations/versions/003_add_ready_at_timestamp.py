"""Add ready_at timestamp to meals

Revision ID: 003
Revises: 
Create Date: 2024-01-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Add ready_at column to meal table."""
    # Add ready_at timestamp column
    op.add_column('meal', sa.Column('ready_at', sa.DateTime(), nullable=True))

def downgrade():
    """Remove ready_at column from meal table."""
    # Remove ready_at timestamp column
    op.drop_column('meal', 'ready_at') 