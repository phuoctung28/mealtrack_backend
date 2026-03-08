"""Create saved_suggestions table.

Revision ID: 031
Revises: 030
Create Date: 2026-03-08 09:00:00.000000

Persistent storage for user-bookmarked meal suggestions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '031'
down_revision: Union[str, None] = '030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'saved_suggestions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(128), nullable=False),
        sa.Column('suggestion_id', sa.String(64), nullable=False),
        sa.Column('meal_type', sa.String(20), nullable=False),
        sa.Column('portion_multiplier', sa.Integer(), server_default='1'),
        sa.Column('suggestion_data', sa.JSON(), nullable=False),
        sa.Column('saved_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'suggestion_id', name='uq_user_suggestion'),
        sa.Index('idx_user_saved', 'user_id', 'saved_at'),
    )


def downgrade() -> None:
    op.drop_table('saved_suggestions')
