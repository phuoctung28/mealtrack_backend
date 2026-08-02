"""Add isolated persistence for paid web leads and claims."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260802000001"
down_revision: str | None = "20260801000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "web_funnel_leads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("access_key_hash", sa.String(64), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False, unique=True),
        sa.Column("snapshot_version", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("payment_verified_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("claimed_uid", sa.String(128), unique=True),
        sa.Column("access_sync_status", sa.String(16), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'checkout_started', 'payment_verified', 'email_queued', 'claim_reserved', 'claimed', 'expired', 'revoked', 'conflict', 'refunded')", name="ck_web_funnel_lead_status"),
        sa.CheckConstraint("access_sync_status IN ('active', 'pending', 'refunded')", name="ck_web_funnel_lead_access_sync_status"),
    )
    op.create_index("ix_web_funnel_leads_access_key_hash", "web_funnel_leads", ["access_key_hash"])
    op.create_index("ix_web_funnel_leads_status", "web_funnel_leads", ["status"])

    op.create_table(
        "web_funnel_claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lead_id", sa.String(36), sa.ForeignKey("web_funnel_leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("magic_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("reservation_retry_secret_hash", sa.String(64)),
        sa.Column("reservation_id", sa.String(36), unique=True),
        sa.Column("reservation_uid", sa.String(128)),
        sa.Column("provisional_reservation_uid", sa.String(128)),
        sa.Column("reservation_expires_at", sa.DateTime(timezone=True)),
        sa.Column("exchange_token_hash", sa.String(64), unique=True),
        sa.Column("exchange_expires_at", sa.DateTime(timezone=True)),
        sa.Column("consumed_uid", sa.String(128)),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("result", sa.JSON()),
        sa.UniqueConstraint("lead_id", "generation", name="uq_web_funnel_claim_generation"),
    )
    op.create_index("ix_web_funnel_claims_lead_id", "web_funnel_claims", ["lead_id"])
    op.create_index("ix_web_funnel_claims_reservation_uid", "web_funnel_claims", ["reservation_uid"])
    op.create_index("ix_web_funnel_claims_reservation_id", "web_funnel_claims", ["reservation_id"])
    op.create_index(
        "uq_web_funnel_claims_active_generation",
        "web_funnel_claims",
        ["lead_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL AND consumed_at IS NULL"),
    )

    for table_name, columns in (
        ("web_funnel_provider_events", [
            sa.Column("id", sa.String(36), primary_key=True), sa.Column("provider_event_id", sa.String(255), nullable=False, unique=True), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("lead_id", sa.String(36)), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("processed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        ]),
        ("web_funnel_outbox", [
            sa.Column("id", sa.String(36), primary_key=True), sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True), sa.Column("job_type", sa.String(64), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False), sa.Column("locked_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("last_error", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="ck_web_funnel_outbox_status"),
        ]),
    ):
        op.create_table(table_name, *columns)
    op.create_index("ix_web_funnel_outbox_due", "web_funnel_outbox", ["status", "next_attempt_at"])


def downgrade() -> None:
    op.drop_index("ix_web_funnel_outbox_due", table_name="web_funnel_outbox")
    op.drop_table("web_funnel_outbox")
    op.drop_table("web_funnel_provider_events")
    op.drop_index("ix_web_funnel_claims_reservation_id", table_name="web_funnel_claims")
    op.drop_index("ix_web_funnel_claims_reservation_uid", table_name="web_funnel_claims")
    op.drop_index("uq_web_funnel_claims_active_generation", table_name="web_funnel_claims")
    op.drop_index("ix_web_funnel_claims_lead_id", table_name="web_funnel_claims")
    op.drop_table("web_funnel_claims")
    op.drop_index("ix_web_funnel_leads_status", table_name="web_funnel_leads")
    op.drop_index("ix_web_funnel_leads_access_key_hash", table_name="web_funnel_leads")
    op.drop_table("web_funnel_leads")
