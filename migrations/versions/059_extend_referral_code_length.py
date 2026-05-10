"""Extend referral code columns from VARCHAR(6) to VARCHAR(15).

Supports admin-created promo codes from 3-15 characters.
Auto-generated user codes remain 6 chars.

Revision ID: 059
Revises: 058
"""
from alembic import op
import sqlalchemy as sa

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "referral_codes",
        "code",
        existing_type=sa.String(6),
        type_=sa.String(15),
        nullable=False,
    )
    op.alter_column(
        "referral_conversions",
        "code_used",
        existing_type=sa.String(6),
        type_=sa.String(15),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "referral_conversions",
        "code_used",
        existing_type=sa.String(15),
        type_=sa.String(6),
        nullable=False,
    )
    op.alter_column(
        "referral_codes",
        "code",
        existing_type=sa.String(15),
        type_=sa.String(6),
        nullable=False,
    )
