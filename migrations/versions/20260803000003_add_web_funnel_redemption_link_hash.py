"""Add hashed RevenueCat redemption-link correlation."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260803000003"
down_revision: str | None = "20260803000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "web_funnel_redemptions",
        sa.Column("redemption_link_hash", sa.String(64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_web_funnel_redemptions_redemption_link_hash",
        "web_funnel_redemptions",
        ["redemption_link_hash"],
    )
    op.create_index(
        "ix_web_funnel_redemptions_redemption_link_hash",
        "web_funnel_redemptions",
        ["redemption_link_hash"],
    )


def downgrade() -> None:
    raise NotImplementedError("This migration is forward-only to protect redemption ownership.")
