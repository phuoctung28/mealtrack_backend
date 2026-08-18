"""Merge catalog popularity-rank and meal-translation-version heads."""

from collections.abc import Sequence

revision: str = "20260818000001"
down_revision: tuple[str, str] = (
    "20260816000005",
    "20260817000001",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record that both independent migration branches have been applied."""


def downgrade() -> None:
    """Keep forward-only production schema changes intact on rollback."""
