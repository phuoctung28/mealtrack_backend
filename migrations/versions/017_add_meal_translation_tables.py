"""add_meal_translation_tables

Revision ID: 017
Revises: 016
Create Date: 2026-01-28 11:31:00.913307

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '017'
down_revision: Union[str, None] = '016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create meal_translation and food_item_translation tables."""
    # Create meal_translation table
    op.create_table(
        'meal_translation',
        sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('meal_id', mysql.VARCHAR(length=36), nullable=False, index=True),
        sa.Column('language', mysql.VARCHAR(length=7), nullable=False),  # ISO 639-1
        sa.Column('dish_name', mysql.VARCHAR(length=255), nullable=False),
        sa.Column('translated_at', mysql.DATETIME(), nullable=False),
        sa.Column('created_at', mysql.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(['meal_id'], ['meal.meal_id'], name='meal_translation_ibfk_1', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('meal_id', 'language', name='uq_meal_language'),
        mysql_collate='utf8mb4_0900_ai_ci',
        mysql_default_charset='utf8mb4',
        mysql_engine='InnoDB'
    )

    # Create food_item_translation table
    op.create_table(
        'food_item_translation',
        sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('meal_translation_id', mysql.INTEGER(), nullable=False),
        sa.Column('food_item_id', mysql.VARCHAR(length=36), nullable=False, index=True),
        sa.Column('name', mysql.VARCHAR(length=255), nullable=False),
        sa.Column('description', mysql.TEXT(), nullable=True),
        sa.ForeignKeyConstraint(['meal_translation_id'], ['meal_translation.id'], name='food_item_translation_ibfk_1', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_collate='utf8mb4_0900_ai_ci',
        mysql_default_charset='utf8mb4',
        mysql_engine='InnoDB'
    )


def downgrade() -> None:
    """Drop meal_translation and food_item_translation tables."""
    op.drop_table('food_item_translation')
    op.drop_table('meal_translation')
