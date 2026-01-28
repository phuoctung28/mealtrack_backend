"""Fix missing meal_type column (idempotent)

Revision ID: 016
Revises: 015
Create Date: 2026-01-28

This migration safely adds the meal_type column if it's missing.
It handles cases where alembic_version was stamped but the column wasn't created.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

revision: str = '016'
down_revision: Union[str, None] = '015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add meal_type column if it doesn't exist"""
    conn = op.get_bind()

    # Check if column exists
    result = conn.execute(text("SHOW COLUMNS FROM meal LIKE 'meal_type'")).fetchall()

    if not result:
        logger.info("Adding missing meal_type column...")
        op.add_column('meal', sa.Column('meal_type', sa.String(length=20), nullable=True))
        op.create_index('idx_meal_type', 'meal', ['meal_type'])
        logger.info("Added meal_type column and index")
    else:
        logger.info("meal_type column already exists, skipping")


def downgrade() -> None:
    """Remove meal_type column if it exists"""
    conn = op.get_bind()

    result = conn.execute(text("SHOW COLUMNS FROM meal LIKE 'meal_type'")).fetchall()

    if result:
        op.drop_index('idx_meal_type', table_name='meal')
        op.drop_column('meal', 'meal_type')
        logger.info("Removed meal_type column and index")
