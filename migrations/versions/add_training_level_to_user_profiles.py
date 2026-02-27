"""add_training_level_to_user_profiles

Revision ID: add_training_level
Revises:
Create Date: 2026-02-27 16:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_training_level'
down_revision: Union[str, None] = '020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'user_profiles',
        sa.Column('training_level', sa.String(20), nullable=True, server_default=None)
    )


def downgrade() -> None:
    op.drop_column('user_profiles', 'training_level')
