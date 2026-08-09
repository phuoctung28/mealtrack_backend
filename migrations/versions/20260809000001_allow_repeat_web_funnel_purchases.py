"""Allow one authenticated account to finalize multiple paid web purchases."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260809000001"
down_revision: str | None = "20260807000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep purchase-row identity unique without making Firebase UID global."""
    op.drop_constraint(
        "web_funnel_leads_claimed_uid_key",
        "web_funnel_leads",
        type_="unique",
    )
    op.drop_constraint(
        "web_funnel_redemptions_redeemer_uid_key",
        "web_funnel_redemptions",
        type_="unique",
    )
    op.drop_constraint(
        "web_funnel_redemptions_finalized_uid_key",
        "web_funnel_redemptions",
        type_="unique",
    )


def downgrade() -> None:
    """Do not reintroduce data-loss-prone global UID uniqueness."""
    raise NotImplementedError(
        "This migration is forward-only to preserve repeat purchase history."
    )
