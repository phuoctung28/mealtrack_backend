"""Remove superseded web funnel claim tables.

The preceding migration remains in the repository because it has already been
applied outside local development. RevenueCat Redemption Links replace these
application-owned records.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260801000002"
down_revision: str | None = "20260801000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("idx_web_funnel_claim_status_expiry", table_name="web_funnel_claims")
    op.drop_table("web_funnel_claims")
    op.drop_index("idx_web_funnel_lead_draft_access", table_name="web_funnel_leads")
    op.drop_index("idx_web_funnel_leads_state", table_name="web_funnel_leads")
    op.drop_index("idx_web_funnel_leads_normalized_email", table_name="web_funnel_leads")
    op.drop_table("web_funnel_leads")


def downgrade() -> None:
    """Keep the forward-only production cleanup in place."""
