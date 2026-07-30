"""Track seen and retired recommendation candidates."""

import sqlalchemy as sa
from alembic import op

revision = "20260727000001"
down_revision = "20260726000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meal_recommendations",
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "meal_recommendations",
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE meal_recommendations SET seen_at = COALESCE(seen_at, created_at) "
        "WHERE is_selected = TRUE"
    )


def downgrade() -> None:
    op.drop_column("meal_recommendations", "retired_at")
    op.drop_column("meal_recommendations", "seen_at")
