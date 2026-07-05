"""Add allowed unit options to food items.

Revision ID: 20260705000001
Revises: 20260702000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260705000001"
down_revision = "20260702000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "food_item",
        "unit",
        existing_type=sa.String(length=50),
        type_=sa.String(length=120),
        existing_nullable=False,
    )
    op.add_column("food_item", sa.Column("allowed_units", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("food_item", "allowed_units")
    op.alter_column(
        "food_item",
        "unit",
        existing_type=sa.String(length=120),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
