"""add dish_name to meal table

Revision ID: add_dish_name_001
Revises: 
Create Date: 2024-06-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add dish_name column to meal table
    op.add_column('meal', sa.Column('dish_name', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove dish_name column from meal table
    op.drop_column('meal', 'dish_name')