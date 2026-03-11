"""evolve_barcode_to_food_reference

Rename barcode_products → food_reference, add new columns,
drop calories_100g (derive from macros), add food_reference_id FK to food_item.

Revision ID: 035
Revises: 034
Create Date: 2026-03-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "035"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename table
    op.rename_table("barcode_products", "food_reference")

    # Add new columns
    op.add_column(
        "food_reference",
        sa.Column("name_vi", sa.String(255), nullable=True),
    )
    op.add_column(
        "food_reference",
        sa.Column("category", sa.String(100), nullable=True),
    )
    op.add_column(
        "food_reference",
        sa.Column("region", sa.String(10), nullable=False, server_default="global"),
    )
    op.add_column(
        "food_reference",
        sa.Column("fdc_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "food_reference",
        sa.Column("fiber_100g", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "food_reference",
        sa.Column("sugar_100g", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "food_reference",
        sa.Column("serving_sizes", sa.JSON(), nullable=True),
    )
    op.add_column(
        "food_reference",
        sa.Column("density", sa.Float(), nullable=False, server_default="1.0"),
    )
    op.add_column(
        "food_reference",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="0"),
    )

    # Drop misleading calories column (derive from macros)
    op.drop_column("food_reference", "calories_100g")

    # Add indexes
    op.create_index("ix_food_reference_fdc_id", "food_reference", ["fdc_id"])
    op.create_index("ix_food_reference_category", "food_reference", ["category"])

    # Add food_reference_id FK to food_item
    op.add_column(
        "food_item",
        sa.Column("food_reference_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_food_item_food_reference",
        "food_item",
        "food_reference",
        ["food_reference_id"],
        ["id"],
    )


def downgrade() -> None:
    # Remove FK from food_item
    op.drop_constraint("fk_food_item_food_reference", "food_item", type_="foreignkey")
    op.drop_column("food_item", "food_reference_id")

    # Remove indexes
    op.drop_index("ix_food_reference_category", "food_reference")
    op.drop_index("ix_food_reference_fdc_id", "food_reference")

    # Re-add calories_100g
    op.add_column(
        "food_reference",
        sa.Column("calories_100g", sa.Float(), nullable=True),
    )

    # Drop new columns (reverse order)
    op.drop_column("food_reference", "is_verified")
    op.drop_column("food_reference", "density")
    op.drop_column("food_reference", "serving_sizes")
    op.drop_column("food_reference", "sugar_100g")
    op.drop_column("food_reference", "fiber_100g")
    op.drop_column("food_reference", "fdc_id")
    op.drop_column("food_reference", "region")
    op.drop_column("food_reference", "category")
    op.drop_column("food_reference", "name_vi")

    # Rename back
    op.rename_table("food_reference", "barcode_products")
