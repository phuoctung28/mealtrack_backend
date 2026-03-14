"""add custom macro columns to user_profiles

Allow users to override calculated macro targets with custom values.
When all three columns are non-null, custom macros take precedence.

Revision ID: 037
Revises: 036
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '037'
down_revision: Union[str, None] = '036'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('custom_protein_g', sa.Float(), nullable=True))
    op.add_column('user_profiles', sa.Column('custom_carbs_g', sa.Float(), nullable=True))
    op.add_column('user_profiles', sa.Column('custom_fat_g', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'custom_fat_g')
    op.drop_column('user_profiles', 'custom_carbs_g')
    op.drop_column('user_profiles', 'custom_protein_g')
