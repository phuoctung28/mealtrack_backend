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


def upgrade() -> None:
    # food_item table
    op.add_column(
        "food_item",
        sa.Column("fiber", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "food_item",
        sa.Column("sugar", sa.Float(), nullable=False, server_default="0"),
    )

    # nutrition table (aggregated totals)
    op.add_column(
        "nutrition",
        sa.Column("fiber", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "nutrition",
        sa.Column("sugar", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("nutrition", "sugar")
    op.drop_column("nutrition", "fiber")
    op.drop_column("food_item", "sugar")
    op.drop_column("food_item", "fiber")
