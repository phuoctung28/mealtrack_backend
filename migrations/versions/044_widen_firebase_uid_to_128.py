"""Widen firebase_uid column from VARCHAR(36) to VARCHAR(128).

Firebase UIDs can be up to 128 characters. The previous VARCHAR(36) limit
could silently truncate UIDs on write, causing webhook lookup mismatches.

Revision ID: 044
Revises: 043
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '044'
down_revision = '043'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'users',
        'firebase_uid',
        existing_type=sa.String(36),
        type_=sa.String(128),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'users',
        'firebase_uid',
        existing_type=sa.String(128),
        type_=sa.String(36),
        existing_nullable=False,
    )
