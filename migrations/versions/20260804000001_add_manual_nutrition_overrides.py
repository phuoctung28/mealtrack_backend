"""Persist independent meal and ingredient nutrition overrides."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804000001"
down_revision: str | None = "20260730110500000000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in ("nutrition", "food_item"):
        if not inspector.has_table(table_name):
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "nutrition_override" not in columns:
            op.add_column(
                table_name,
                sa.Column("nutrition_override", sa.JSON(), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in ("food_item", "nutrition"):
        if not inspector.has_table(table_name):
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "nutrition_override" in columns:
            op.drop_column(table_name, "nutrition_override")
