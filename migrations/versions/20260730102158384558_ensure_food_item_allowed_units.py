"""Ensure legacy deployments expose food item allowed units."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730102158384558"
down_revision: str | None = "20260730000004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("food_item"):
        return

    columns = {column["name"] for column in inspector.get_columns("food_item")}
    if "allowed_units" in columns:
        return

    op.add_column("food_item", sa.Column("allowed_units", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Preserve a column that may have existed before this forward repair."""
