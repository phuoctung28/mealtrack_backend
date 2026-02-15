"""add_barcode_products_table

Revision ID: 018
Revises: 017
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '018'
down_revision: Union[str, None] = '017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'barcode_products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('barcode', sa.String(20), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('brand', sa.String(255), nullable=True),
        sa.Column('calories_100g', sa.Float(), nullable=True),
        sa.Column('protein_100g', sa.Float(), nullable=True),
        sa.Column('carbs_100g', sa.Float(), nullable=True),
        sa.Column('fat_100g', sa.Float(), nullable=True),
        sa.Column('serving_size', sa.String(100), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('source', sa.String(50), nullable=True, server_default='fatsecret'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('barcode'),
    )
    op.create_index('ix_barcode_products_barcode', 'barcode_products', ['barcode'])


def downgrade() -> None:
    op.drop_index('ix_barcode_products_barcode', table_name='barcode_products')
    op.drop_table('barcode_products')
