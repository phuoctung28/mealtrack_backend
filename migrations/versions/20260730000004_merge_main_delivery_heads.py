"""Merge the delivery recommendation and body-fat migration branches."""

from typing import Sequence, Union


revision: str = "20260730000004"
down_revision: Union[str, Sequence[str], None] = (
    "20260727000001",
    "20260730000003",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
