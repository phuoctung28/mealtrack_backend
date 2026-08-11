"""Add verified RevenueCat web-customer redemption bindings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260803000001"
down_revision: str | None = "20260802000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "revenuecat_customer_id",
        existing_type=sa.String(length=36),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.create_table(
        "web_funnel_redemptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "lead_id",
            sa.String(36),
            sa.ForeignKey("web_funnel_leads.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("project", sa.String(128), nullable=False),
        sa.Column("original_app_user_id", sa.String(255), nullable=False),
        sa.Column("verified_app_user_id", sa.String(255), nullable=False),
        sa.Column("entitlement_id", sa.String(128), nullable=False),
        sa.Column("product_id", sa.String(255), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_uid", sa.String(128), unique=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.Column("redeemer_uid", sa.String(128), unique=True),
        sa.Column("redemption_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("finalization_key_hash", sa.String(64), unique=True),
        sa.Column("result", sa.JSON()),
        sa.UniqueConstraint(
            "provider",
            "project",
            "environment",
            "original_app_user_id",
            name="uq_web_funnel_redemptions_provider_customer",
        ),
    )
    op.create_index(
        "ix_web_funnel_redemptions_finalized_uid",
        "web_funnel_redemptions",
        ["finalized_uid"],
    )


def downgrade() -> None:
    raise NotImplementedError(
        "This migration is forward-only to protect provider identifiers."
    )
