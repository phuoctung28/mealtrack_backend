"""Add feature flags table

Revision ID: 003
Revises: 002
Create Date: 2024-08-31 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create feature_flags table"""
    
    op.create_table('feature_flags',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('name')
    )
    
    # Create index on name column for faster lookups
    op.create_index(op.f('ix_feature_flags_name'), 'feature_flags', ['name'], unique=False)


def downgrade() -> None:
    """Drop feature_flags table"""
    
    op.drop_index(op.f('ix_feature_flags_name'), table_name='feature_flags')
    op.drop_table('feature_flags')