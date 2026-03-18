"""Add extra_nutrients JSON column to food_reference.

Revision ID: 038
Revises: 037
Create Date: 2026-03-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "038"
down_revision: Union[str, None] = "037"
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
    if not _has_column("food_reference", "extra_nutrients"):
        op.add_column(
            "food_reference",
            sa.Column("extra_nutrients", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    if _has_column("food_reference", "extra_nutrients"):
        op.drop_column("food_reference", "extra_nutrients")
