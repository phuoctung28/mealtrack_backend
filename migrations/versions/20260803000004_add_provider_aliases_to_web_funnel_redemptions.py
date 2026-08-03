"""Persist all RevenueCat aliases observed during redemption."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260803000004"
down_revision: str | None = "20260803000003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "web_funnel_redemptions",
        sa.Column("provider_app_user_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    raise NotImplementedError(
        "This migration is forward-only to protect provider identifiers."
    )
