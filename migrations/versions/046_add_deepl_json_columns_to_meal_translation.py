"""Add meal_instruction and meal_ingredients JSON columns to meal_translation.

Stores translated instructions and ingredients directly on the translation row,
enabling the DeepL cache check without joining food_item_translation.

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
        'meal_translation',
        sa.Column('meal_instruction', sa.JSON, nullable=True)
    )
    op.add_column(
        'meal_translation',
        sa.Column('meal_ingredients', sa.JSON, nullable=True)
    )


def downgrade() -> None:
    op.drop_column('meal_translation', 'meal_ingredients')
    op.drop_column('meal_translation', 'meal_instruction')
