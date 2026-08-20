"""Add the explicit curated ordering signal for public catalog discovery."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816000005"
down_revision: str | None = "20260815000004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "meal_catalog",
        sa.Column("popularity_rank", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_meal_catalog_popularity_rank_non_negative",
        "meal_catalog",
        "popularity_rank IS NULL OR popularity_rank >= 0",
    )
    op.create_index(
        "idx_meal_catalog_active_popularity",
        "meal_catalog",
        ["is_active", "popularity_rank", "name", "id"],
    )


def downgrade() -> None:
    op.drop_index("idx_meal_catalog_active_popularity", table_name="meal_catalog")
    op.drop_constraint(
        "ck_meal_catalog_popularity_rank_non_negative",
        "meal_catalog",
        type_="check",
    )
    op.drop_column("meal_catalog", "popularity_rank")
