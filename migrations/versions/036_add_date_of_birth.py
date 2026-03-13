"""add_date_of_birth

Add date_of_birth column to user_profiles for storing DOB alongside age.
Age is still computed from DOB for TDEE calculations.

Revision ID: 036
Revises: 035
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '036'
down_revision: Union[str, None] = '035'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('date_of_birth', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'date_of_birth')
