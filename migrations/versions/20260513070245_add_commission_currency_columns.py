"""Add commission_currency and commission_amount_vnd columns.

Revision ID: 20260513070245
Revises: 20260512162000
Create Date: 2026-05-13 07:02:45

"""

import sqlalchemy as sa
from alembic import op

revision = "20260513070245"
down_revision = "20260512162000"
branch_labels = None
depends_on = None


def upgrade():
    # Change commission_amount from Integer to Float for non-integer currencies (EUR 1.8)
    op.alter_column(
        "referral_conversions",
        "commission_amount",
        type_=sa.Float,
        existing_type=sa.Integer,
        existing_nullable=False,
    )
    op.add_column(
        "referral_conversions",
        sa.Column("commission_currency", sa.String(3), nullable=True, server_default="VND"),
    )
    op.add_column(
        "referral_conversions",
        sa.Column("commission_amount_vnd", sa.Integer, nullable=True),
    )
    # Backfill: existing rows are VND, so commission_amount_vnd = commission_amount
    op.execute(
        "UPDATE referral_conversions "
        "SET commission_currency = 'VND', commission_amount_vnd = CAST(commission_amount AS INTEGER) "
        "WHERE commission_currency IS NULL"
    )


def downgrade():
    op.drop_column("referral_conversions", "commission_amount_vnd")
    op.drop_column("referral_conversions", "commission_currency")
    op.alter_column(
        "referral_conversions",
        "commission_amount",
        type_=sa.Integer,
        existing_type=sa.Float,
        existing_nullable=False,
    )
