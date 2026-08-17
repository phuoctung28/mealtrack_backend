"""Persist the display locale selected when an image meal is created."""

import sqlalchemy as sa
from alembic import op

revision = "20260817000002"
down_revision = "20260817000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a nullable locale marker while preserving legacy meal behavior."""
    op.add_column(
        "meal",
        sa.Column("display_language", sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    """Remove the persisted display locale marker."""
    op.drop_column("meal", "display_language")
