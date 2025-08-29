"""Remove test table if exists

Revision ID: 003
Revises: 002
Create Date: 2024-08-28 23:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove test table if it exists"""
    
    # Check if test_table exists and drop it
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if 'test_table' in inspector.get_table_names():
        op.drop_table('test_table')
        logger.info("✅ Removed test_table")
    else:
        logger.info("ℹ️  test_table does not exist, nothing to remove")


def downgrade() -> None:
    """Recreate test table if it was removed"""
    
    # Recreate test_table
    op.create_table('test_table',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('test_number', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Recreated test_table")