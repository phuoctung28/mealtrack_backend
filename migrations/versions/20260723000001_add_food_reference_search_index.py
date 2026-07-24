"""Add trigram index for local food-reference search.

Revision ID: 20260723000001
Revises: 20260716000001
"""

from alembic import op

revision = "20260723000001"
down_revision = "20260716000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ux_food_reference_name_normalized",
        "food_reference",
        ["name_normalized"],
        unique=True,
    )
    op.create_index(
        "ix_food_reference_name_normalized_trgm",
        "food_reference",
        ["name_normalized"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name_normalized": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_food_reference_name_normalized_trgm",
        table_name="food_reference",
        postgresql_using="gin",
    )
    op.drop_index("ux_food_reference_name_normalized", table_name="food_reference")
