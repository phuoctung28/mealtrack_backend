"""Add subscription trial offer state.

Revision ID: 20260702000002
Revises: 20260702000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260702000002"
down_revision = "20260702000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions", sa.Column("period_type", sa.String(32), nullable=True)
    )
    op.add_column(
        "subscriptions",
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "subscriptions", sa.Column("cancel_reason", sa.String(64), nullable=True)
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "trial_end_discount_claimed_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column("trial_end_discount_product_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("trial_end_discount_identifier", sa.String(255), nullable=True),
    )
    op.create_index(
        "idx_subscription_trial_offer_candidates",
        "subscriptions",
        ["status", "expires_at", "period_type", "trial_end_discount_claimed_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_subscription_trial_offer_candidates", table_name="subscriptions")
    op.drop_column("subscriptions", "trial_end_discount_identifier")
    op.drop_column("subscriptions", "trial_end_discount_product_id")
    op.drop_column("subscriptions", "trial_end_discount_claimed_at")
    op.drop_column("subscriptions", "cancel_reason")
    op.drop_column("subscriptions", "trial_expires_at")
    op.drop_column("subscriptions", "trial_started_at")
    op.drop_column("subscriptions", "period_type")
