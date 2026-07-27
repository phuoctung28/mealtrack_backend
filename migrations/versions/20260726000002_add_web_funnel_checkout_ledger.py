"""Add web funnel checkout ledger.

Revision ID: 20260726000002
Revises: 20260726000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260726000002"
down_revision = "20260726000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_funnel_leads",
        sa.Column("external_lead_id", sa.String(length=128), nullable=False),
        sa.Column("email_hash", sa.String(length=64), nullable=True),
        sa.Column("first_seen_country", sa.String(length=2), nullable=True),
        sa.Column("last_seen_country", sa.String(length=2), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_lead_id"),
    )
    op.create_index(
        op.f("ix_web_funnel_leads_external_lead_id"),
        "web_funnel_leads",
        ["external_lead_id"],
        unique=False,
    )

    op.create_table(
        "web_funnel_checkouts",
        sa.Column("lead_id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), server_default="pending_approval", nullable=False),
        sa.Column("state_reason", sa.String(length=255), nullable=True),
        sa.Column("offer_id", sa.String(length=64), nullable=False),
        sa.Column("reward_id", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=16), nullable=False),
        sa.Column("billing_country", sa.String(length=2), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("renewal_interval", sa.String(length=16), nullable=False),
        sa.Column("welcome_discount_percent", sa.Integer(), nullable=False),
        sa.Column("provider_plan_id", sa.String(length=255), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("provider_customer_id", sa.String(length=255), nullable=True),
        sa.Column("provider_transaction_id", sa.String(length=255), nullable=True),
        sa.Column("custom_id_hash", sa.String(length=64), nullable=False),
        sa.Column("claim_token_hash", sa.String(length=64), nullable=False),
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_minor >= 0", name="ck_web_funnel_amount_nonnegative"),
        sa.ForeignKeyConstraint(["lead_id"], ["web_funnel_leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("custom_id_hash"),
        sa.UniqueConstraint("claim_token_hash"),
        sa.UniqueConstraint("lead_id", "idempotency_key_hash", name="uq_web_funnel_checkout_lead_idempotency"),
        sa.UniqueConstraint("provider", "provider_subscription_id", name="uq_web_funnel_checkout_provider_subscription"),
    )
    op.create_index("idx_web_funnel_checkouts_lead_state", "web_funnel_checkouts", ["lead_id", "state"], unique=False)
    op.create_index("idx_web_funnel_checkouts_state", "web_funnel_checkouts", ["state"], unique=False)

    op.create_table(
        "web_funnel_provider_events",
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("checkout_id", sa.String(length=36), nullable=True),
        sa.Column("verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("processed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("processing_result", sa.String(length=64), nullable=False),
        sa.Column("safe_payload", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["checkout_id"], ["web_funnel_checkouts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_id", name="uq_web_funnel_provider_event"),
    )
    op.create_index("idx_web_funnel_provider_events_checkout", "web_funnel_provider_events", ["checkout_id"], unique=False)
    op.create_index(op.f("ix_web_funnel_provider_events_provider_subscription_id"), "web_funnel_provider_events", ["provider_subscription_id"], unique=False)

    op.create_table(
        "web_funnel_claims",
        sa.Column("checkout_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("claim_token_hash", sa.String(length=64), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["checkout_id"], ["web_funnel_checkouts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checkout_id"),
        sa.UniqueConstraint("claim_token_hash"),
    )
    op.create_index("idx_web_funnel_claims_user", "web_funnel_claims", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_web_funnel_claims_user", table_name="web_funnel_claims")
    op.drop_table("web_funnel_claims")
    op.drop_index(op.f("ix_web_funnel_provider_events_provider_subscription_id"), table_name="web_funnel_provider_events")
    op.drop_index("idx_web_funnel_provider_events_checkout", table_name="web_funnel_provider_events")
    op.drop_table("web_funnel_provider_events")
    op.drop_index("idx_web_funnel_checkouts_state", table_name="web_funnel_checkouts")
    op.drop_index("idx_web_funnel_checkouts_lead_state", table_name="web_funnel_checkouts")
    op.drop_table("web_funnel_checkouts")
    op.drop_index(op.f("ix_web_funnel_leads_external_lead_id"), table_name="web_funnel_leads")
    op.drop_table("web_funnel_leads")
