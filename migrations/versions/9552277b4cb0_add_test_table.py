"""add_test_table

Revision ID: 9552277b4cb0
Revises: 001
Create Date: 2025-08-27 18:27:09.665801

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger(__name__)


# revision identifiers, used by Alembic.
revision: str = '9552277b4cb0'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create test_table
    op.create_table('test_table',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('test_number', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created test_table")


def downgrade() -> None:
    # Drop test_table
    op.drop_table('test_table')
    logger.info("✅ Dropped test_table")