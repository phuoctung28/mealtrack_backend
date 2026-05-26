"""Add quantity column to meal table.

quantity stores the serving size: grams for food meals, ml for hydration meals.

Revision ID: 20260525000001
Revises: 20260523000001
"""
import sqlalchemy as sa
from alembic import op

revision = "20260525000001"
down_revision = "20260523000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meal",
        sa.Column("quantity", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meal", "quantity")
