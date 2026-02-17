"""add_cheat_meal_columns

Revision ID: 020
Revises: 019
Create Date: 2026-02-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '020'
down_revision: Union[str, None] = '019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('meal', sa.Column('is_cheat_meal', sa.Boolean(), default=False, nullable=False))
    op.add_column('meal', sa.Column('cheat_tagged_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('meal', 'cheat_tagged_at')
    op.drop_column('meal', 'is_cheat_meal')
