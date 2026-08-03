"""Merge Paddle fulfillment and catalog repair migration heads."""

from collections.abc import Sequence

revision: str = "20260731121600000000"
down_revision: tuple[str, str] = (
    "20260730110500000000",
    "20260731000001",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record that both independent migration branches have been applied."""


def downgrade() -> None:
    """Keep forward-only production schema changes intact on rollback."""
