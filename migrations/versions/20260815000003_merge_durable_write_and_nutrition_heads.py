"""Merge durable-write and nutrition-integrity migration branches."""

from collections.abc import Sequence

revision: str = "20260815000003"
down_revision: tuple[str, str] = ("20260811000001", "20260815000002")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
