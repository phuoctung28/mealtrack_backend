"""Add order_index column to food_item for stable ingredient ordering.

Revision ID: 040
Revises: 039
Create Date: 2026-03-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "040"
down_revision: Union[str, None] = "039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
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
    if not _has_column("food_item", "order_index"):
        op.add_column(
            "food_item",
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _has_column("food_item", "order_index"):
        op.drop_column("food_item", "order_index")
