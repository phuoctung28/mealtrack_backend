"""Add name_normalized column to food_reference for deterministic ingredient matching.

Stores the lowercased, qualifier-stripped form of food names to enable
consistent fuzzy matching without re-normalizing on every query.

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
        'food_reference',
        sa.Column('name_normalized', sa.String(255), nullable=True),
    )
    op.create_index(
        'ix_food_reference_name_normalized',
        'food_reference',
        ['name_normalized'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_food_reference_name_normalized', table_name='food_reference')
    op.drop_column('food_reference', 'name_normalized')
