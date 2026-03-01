"""add_training_level_to_user_profiles

Revision ID: 022
Revises: 021
Create Date: 2026-02-27

Add training_level column for training-level-aware protein calculation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '022'
down_revision: Union[str, None] = '021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'user_profiles',
        sa.Column('training_level', sa.String(20), nullable=True, server_default=None)
    )


def downgrade() -> None:
    op.drop_column('user_profiles', 'training_level')
