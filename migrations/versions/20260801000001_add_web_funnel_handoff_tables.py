"""Add durable web funnel lead and claim records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801000001"
down_revision: str | None = "20260731121600000000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "web_funnel_leads",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalized_email", sa.String(length=254), nullable=False),
        sa.Column("draft_access_key_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_revision", sa.String(length=32), nullable=False),
        sa.Column("onboarding_payload", sa.JSON(), nullable=True),
        sa.Column("plan_snapshot", sa.JSON(), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column(
            "access_sync_status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("revenuecat_app_user_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("revenuecat_transaction_id", sa.String(length=255), nullable=True, unique=True),
        sa.Column("revenuecat_store", sa.String(length=32), nullable=True),
        sa.Column("payment_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_web_funnel_leads_normalized_email", "web_funnel_leads", ["normalized_email"])
    op.create_index("idx_web_funnel_leads_state", "web_funnel_leads", ["state"])
    op.create_index("idx_web_funnel_lead_draft_access", "web_funnel_leads", ["normalized_email", "draft_access_key_hash"])
    op.create_table(
        "web_funnel_claims",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("web_funnel_leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("lead_id", "generation", name="uq_web_funnel_claim_generation"),
    )
    op.create_index("idx_web_funnel_claim_status_expiry", "web_funnel_claims", ["status", "expires_at"])


def downgrade() -> None:
    """Keep customer-identity records available for forward-only releases."""
