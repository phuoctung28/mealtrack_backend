"""Merge main nutrition/age migrations with delivery web-funnel head."""

from collections.abc import Sequence

revision: str = "20260807000002"
down_revision: tuple[str, str] = (
    "20260803000004",
    "20260807000001",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record that both independent migration branches have been applied."""


def downgrade() -> None:
    """Keep forward-only production schema changes intact on rollback."""
