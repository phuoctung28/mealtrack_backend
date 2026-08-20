"""Add nullable catalog_meal_id on meal and backfill from slot logs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819000001"
down_revision: str | None = "20260818000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "meal",
        sa.Column("catalog_meal_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_meal_catalog_meal_id",
        "meal",
        "meal_catalog",
        ["catalog_meal_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_meal_user_catalog_meal",
        "meal",
        ["user_id", "catalog_meal_id"],
        postgresql_where=sa.text("catalog_meal_id IS NOT NULL"),
    )
    op.execute(
        """
        UPDATE meal
        SET catalog_meal_id = r.catalog_meal_id
        FROM meal_recommendations r
        WHERE r.logged_meal_id = meal.meal_id
          AND r.logged_meal_id IS NOT NULL
          AND r.catalog_meal_id IS NOT NULL
        """
    )


def downgrade() -> None:
    """Keep forward-only production schema changes intact on rollback."""
