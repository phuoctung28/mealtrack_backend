"""Add pain_points field to user_profiles table

Revision ID: 011
Revises: 010
Create Date: 2024-12-18 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pain_points JSON column to user_profiles table."""
    # Step 1: Add column as nullable (MySQL doesn't allow default for JSON)
    op.add_column(
        'user_profiles',
        sa.Column('pain_points', sa.JSON(), nullable=True)
    )

    # Step 2: Update existing rows with empty array
    op.execute("UPDATE user_profiles SET pain_points = JSON_ARRAY()")

    # Step 3: Make column non-nullable
    op.alter_column(
        'user_profiles',
        'pain_points',
        existing_type=sa.JSON(),
        nullable=False
    )
    logger.info("✅ Added pain_points column to user_profiles table")


def downgrade() -> None:
    """Remove pain_points column from user_profiles table."""
    op.drop_column('user_profiles', 'pain_points')
    logger.info("✅ Removed pain_points column from user_profiles table")
