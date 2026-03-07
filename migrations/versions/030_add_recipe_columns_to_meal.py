"""Add recipe columns to meal table.

Revision ID: 030
Revises: 029
Create Date: 2026-03-06 21:06:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '030'
down_revision: Union[str, None] = '029'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('meal', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('meal', sa.Column('instructions', sa.JSON(), nullable=True))
    op.add_column('meal', sa.Column('prep_time_min', sa.Integer(), nullable=True))
    op.add_column('meal', sa.Column('cook_time_min', sa.Integer(), nullable=True))
    op.add_column('meal', sa.Column('cuisine_type', sa.String(50), nullable=True))
    op.add_column('meal', sa.Column('origin_country', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('meal', 'origin_country')
    op.drop_column('meal', 'cuisine_type')
    op.drop_column('meal', 'cook_time_min')
    op.drop_column('meal', 'prep_time_min')
    op.drop_column('meal', 'instructions')
    op.drop_column('meal', 'description')
