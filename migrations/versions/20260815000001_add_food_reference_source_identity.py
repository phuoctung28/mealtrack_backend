"""Persist explicit namespaces for opaque food-reference source identities."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815000001"
down_revision: str | None = "20260807000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("food_reference"):
        return

    columns = {column["name"] for column in inspector.get_columns("food_reference")}
    if "source_namespace" not in columns:
        op.add_column(
            "food_reference",
            sa.Column("source_namespace", sa.String(length=64), nullable=True),
        )
    if "source_food_id" not in columns:
        op.add_column(
            "food_reference",
            sa.Column("source_food_id", sa.String(length=255), nullable=True),
        )

    index_names = {index["name"] for index in inspector.get_indexes("food_reference")}
    if "uq_food_reference_source_identity" not in index_names:
        op.create_index(
            "uq_food_reference_source_identity",
            "food_reference",
            ["source_namespace", "source_food_id"],
            unique=True,
            postgresql_where=sa.text(
                "source_namespace IS NOT NULL AND source_food_id IS NOT NULL"
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("food_reference"):
        return

    index_names = {index["name"] for index in inspector.get_indexes("food_reference")}
    if "uq_food_reference_source_identity" in index_names:
        op.drop_index("uq_food_reference_source_identity", table_name="food_reference")

    columns = {column["name"] for column in inspector.get_columns("food_reference")}
    if "source_food_id" in columns:
        op.drop_column("food_reference", "source_food_id")
    if "source_namespace" in columns:
        op.drop_column("food_reference", "source_namespace")
