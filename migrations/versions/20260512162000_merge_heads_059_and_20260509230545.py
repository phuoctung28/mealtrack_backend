"""Merge Alembic heads 059 and 20260509230545.

Revision ID: 20260512162000
Revises: 059, 20260509230545
Create Date: 2026-05-12 16:20:00
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "20260512162000"
down_revision: Union[str, Sequence[str], None] = ("059", "20260509230545")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
