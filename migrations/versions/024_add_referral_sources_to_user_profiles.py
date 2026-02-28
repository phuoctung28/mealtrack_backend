"""add_referral_sources_to_user_profiles

Revision ID: 024
Revises: 023
Create Date: 2026-02-28

Add referral_sources JSON column to user_profiles table for attribution tracking.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '024'
down_revision: Union[str, None] = '023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('referral_sources', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'referral_sources')
