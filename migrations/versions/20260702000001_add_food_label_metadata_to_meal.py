"""Add food label metadata to meal.

Revision ID: 20260702000001
Revises: 20260624000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260702000001"
down_revision = "20260624000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meal",
        sa.Column("food_label_metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meal", "food_label_metadata")
