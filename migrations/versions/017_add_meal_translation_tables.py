"""add_meal_translation_tables

Revision ID: 017
Revises: 016
Create Date: 2026-01-28 11:31:00.913307

This migration is idempotent - safe to run multiple times.
"""
from typing import Sequence, Union
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '017'
down_revision: Union[str, None] = '016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(f"SHOW TABLES LIKE '{table_name}'")).fetchall()
    return len(result) > 0


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    conn = op.get_bind()
    result = conn.execute(text(f"SHOW INDEX FROM {table_name} WHERE Key_name = '{index_name}'")).fetchall()
    return len(result) > 0


def upgrade() -> None:
    """Create meal_translation and food_item_translation tables (idempotent)."""

    # Create meal_translation table if not exists
    if not table_exists('meal_translation'):
        logger.info("Creating meal_translation table...")
        op.create_table(
            'meal_translation',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('meal_id', sa.CHAR(36), nullable=False),  # CHAR(36) to match meal.meal_id
            sa.Column('language', sa.String(7), nullable=False),
            sa.Column('dish_name', sa.String(255), nullable=False),
            sa.Column('translated_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['meal_id'], ['meal.meal_id'], name='meal_translation_ibfk_1', ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('meal_id', 'language', name='uq_meal_language')
        )
        logger.info("Created meal_translation table")
    else:
        logger.info("meal_translation table already exists, skipping")

    # Create index for meal_id if not exists
    if table_exists('meal_translation') and not index_exists('meal_translation', 'idx_meal_translation_meal_id'):
        op.create_index('idx_meal_translation_meal_id', 'meal_translation', ['meal_id'])
        logger.info("Created index idx_meal_translation_meal_id")

    # Create food_item_translation table if not exists
    if not table_exists('food_item_translation'):
        logger.info("Creating food_item_translation table...")
        op.create_table(
            'food_item_translation',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('meal_translation_id', sa.Integer(), nullable=False),
            sa.Column('food_item_id', sa.CHAR(36), nullable=False),  # CHAR(36) for consistency
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['meal_translation_id'], ['meal_translation.id'], name='food_item_translation_ibfk_1', ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        logger.info("Created food_item_translation table")
    else:
        logger.info("food_item_translation table already exists, skipping")

    # Create index for food_item_id if not exists
    if table_exists('food_item_translation') and not index_exists('food_item_translation', 'idx_food_item_translation_food_item_id'):
        op.create_index('idx_food_item_translation_food_item_id', 'food_item_translation', ['food_item_id'])
        logger.info("Created index idx_food_item_translation_food_item_id")

    logger.info("Migration 017 completed successfully")


def downgrade() -> None:
    """Drop meal_translation and food_item_translation tables (idempotent)."""
    if table_exists('food_item_translation'):
        if index_exists('food_item_translation', 'idx_food_item_translation_food_item_id'):
            op.drop_index('idx_food_item_translation_food_item_id', table_name='food_item_translation')
        op.drop_table('food_item_translation')

    if table_exists('meal_translation'):
        if index_exists('meal_translation', 'idx_meal_translation_meal_id'):
            op.drop_index('idx_meal_translation_meal_id', table_name='meal_translation')
        op.drop_table('meal_translation')
