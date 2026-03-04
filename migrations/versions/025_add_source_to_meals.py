"""add_source_to_meals

Revision ID: 025
Revises: 024
Create Date: 2026-03-03

Add source column to meal table to track meal creation origin
(scanner, prompt, food_search, manual).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '025'
down_revision: Union[str, None] = '024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('meal', sa.Column('source', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('meal', 'source')
