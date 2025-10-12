"""Add meal_type column to meal table

Revision ID: 006
Revises: 005
Create Date: 2025-10-04 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add meal_type column to meal table"""
    
    # Add meal_type column to meal table
    op.add_column('meal', sa.Column('meal_type', sa.String(length=20), nullable=True))
    logger.info("✅ Added meal_type column to meal table")
    
    # Add index for performance
    op.create_index('idx_meal_type', 'meal', ['meal_type'])
    logger.info("✅ Created index on meal_type column")


def downgrade() -> None:
    """Remove meal_type column from meal table"""
    
    # Drop index
    op.drop_index('idx_meal_type', table_name='meal')
    logger.info("✅ Dropped index on meal_type column")
    
    # Drop column
    op.drop_column('meal', 'meal_type')
    logger.info("✅ Dropped meal_type column from meal table")

