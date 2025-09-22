"""Add meal edit support

Revision ID: 004
Revises: 003
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add meal edit tracking fields and food item editing support"""
    
    # Add edit tracking fields to meal table
    op.add_column('meal', sa.Column('last_edited_at', sa.DateTime(), nullable=True))
    op.add_column('meal', sa.Column('edit_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('meal', sa.Column('is_manually_edited', sa.Boolean(), nullable=False, server_default='0'))
    
    # Add editing support fields to food_item table
    op.add_column('food_item', sa.Column('fdc_id', sa.Integer(), nullable=True))
    op.add_column('food_item', sa.Column('is_custom', sa.Boolean(), nullable=False, server_default='0'))
    
    # Create indexes for better query performance
    op.create_index('ix_meal_edited', 'meal', ['is_manually_edited', 'last_edited_at'])
    op.create_index('ix_food_item_fdc', 'food_item', ['fdc_id'])
    op.create_index('ix_food_item_custom', 'food_item', ['is_custom'])


def downgrade() -> None:
    """Remove meal edit support"""
    
    # Drop indexes
    op.drop_index('ix_food_item_custom', table_name='food_item')
    op.drop_index('ix_food_item_fdc', table_name='food_item')
    op.drop_index('ix_meal_edited', table_name='meal')
    
    # Remove food_item columns
    op.drop_column('food_item', 'is_custom')
    op.drop_column('food_item', 'fdc_id')
    
    # Remove meal columns
    op.drop_column('meal', 'is_manually_edited')
    op.drop_column('meal', 'edit_count')
    op.drop_column('meal', 'last_edited_at')
