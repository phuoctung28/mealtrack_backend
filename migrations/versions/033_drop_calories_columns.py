"""drop_calories_columns

Remove stored calories from food_item and nutrition tables.
Calories are now always derived: protein*4 + carbs*4 + fat*9.

Revision ID: 033
Revises: 032
Create Date: 2026-03-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '033'
down_revision: Union[str, None] = '032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop calories column from food_item table
    op.drop_column('food_item', 'calories')

    # Drop calories column from nutrition table
    op.drop_column('nutrition', 'calories')


def downgrade() -> None:
    # Re-add calories column to nutrition table with default 0
    op.add_column('nutrition', sa.Column('calories', sa.Float(), nullable=False, server_default='0'))

    # Re-add calories column to food_item table with default 0
    op.add_column('food_item', sa.Column('calories', sa.Float(), nullable=False, server_default='0'))
