"""soft_delete_support_for_meal_deletion

Revision ID: 027
Revises: 026
Create Date: 2026-03-04 22:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '027'
down_revision: Union[str, None] = '026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    if not table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # food_item: soft-delete + nullable FK
    if table_exists('food_item'):
        if not column_exists('food_item', 'is_deleted'):
            op.add_column('food_item', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        # Make nutrition_id nullable for orphaned items
        op.alter_column('food_item', 'nutrition_id', existing_type=sa.Integer(), nullable=True)

    # meal_translation: soft-delete + nullable FK + remove CASCADE
    if table_exists('meal_translation'):
        # First, check and drop the foreign key with CASCADE
        bind = op.get_bind()
        inspector = inspect(bind)
        foreign_keys = inspector.get_foreign_keys('meal_translation')
        for fk in foreign_keys:
            if fk.get('name') == 'meal_translation_ibfk_1':
                op.drop_constraint('meal_translation_ibfk_1', 'meal_translation', type_='foreignkey')

        # Add is_deleted column
        if not column_exists('meal_translation', 'is_deleted'):
            op.add_column('meal_translation', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))

        # Make meal_id nullable
        op.alter_column('meal_translation', 'meal_id', existing_type=sa.String(36), nullable=True)

        # Recreate FK without CASCADE
        op.create_foreign_key('meal_translation_ibfk_1', 'meal_translation', 'meal', ['meal_id'], ['meal_id'])

    # food_item_translation: soft-delete only (no FK constraint exists)
    if table_exists('food_item_translation'):
        if not column_exists('food_item_translation', 'is_deleted'):
            op.add_column('food_item_translation', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    # food_item_translation: remove is_deleted
    if table_exists('food_item_translation') and column_exists('food_item_translation', 'is_deleted'):
        op.drop_column('food_item_translation', 'is_deleted')

    # meal_translation: revert changes
    if table_exists('meal_translation'):
        # Drop the FK without CASCADE
        op.drop_constraint('meal_translation_ibfk_1', 'meal_translation', type_='foreignkey')
        # Make meal_id not nullable
        op.alter_column('meal_translation', 'meal_id', existing_type=sa.String(36), nullable=False)
        # Recreate FK with CASCADE
        op.create_foreign_key('meal_translation_ibfk_1', 'meal_translation', 'meal', ['meal_id'], ['meal_id'], ondelete='CASCADE')
        # Remove is_deleted
        if column_exists('meal_translation', 'is_deleted'):
            op.drop_column('meal_translation', 'is_deleted')

    # food_item: revert changes
    if table_exists('food_item'):
        # Make nutrition_id not nullable
        op.alter_column('food_item', 'nutrition_id', existing_type=sa.Integer(), nullable=False)
        # Remove is_deleted
        if column_exists('food_item', 'is_deleted'):
            op.drop_column('food_item', 'is_deleted')
