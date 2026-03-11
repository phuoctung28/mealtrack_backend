"""add_fiber_sugar_columns

Add fiber and sugar columns to food_item and nutrition tables.
Enables fiber-aware calorie formula: P*4 + (C-fiber)*4 + fiber*2 + F*9.

Revision ID: 034
Revises: 033
Create Date: 2026-03-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "034"
down_revision: Union[str, None] = "033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    """Check if a column already exists in the table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.scalar() > 0


def upgrade() -> None:
    # food_item table
    if not _has_column("food_item", "fiber"):
        op.add_column(
            "food_item",
            sa.Column("fiber", sa.Float(), nullable=False, server_default="0"),
        )
    if not _has_column("food_item", "sugar"):
        op.add_column(
            "food_item",
            sa.Column("sugar", sa.Float(), nullable=False, server_default="0"),
        )

    # nutrition table (aggregated totals)
    if not _has_column("nutrition", "fiber"):
        op.add_column(
            "nutrition",
            sa.Column("fiber", sa.Float(), nullable=False, server_default="0"),
        )
    if not _has_column("nutrition", "sugar"):
        op.add_column(
            "nutrition",
            sa.Column("sugar", sa.Float(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    op.drop_column("nutrition", "sugar")
    op.drop_column("nutrition", "fiber")
    op.drop_column("food_item", "sugar")
    op.drop_column("food_item", "fiber")
