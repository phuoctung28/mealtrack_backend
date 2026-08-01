"""Add provider-neutral Paddle fields to existing user and subscription records.

This forward-only migration preserves live billing and fulfillment state.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731000001"
down_revision: str | None = "20260730000004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("paddle_customer_id", sa.String(64), nullable=True))
    op.create_unique_constraint(
        "uq_users_paddle_customer_id", "users", ["paddle_customer_id"]
    )

    op.alter_column(
        "subscriptions",
        "user_id",
        existing_type=sa.String(36),
        nullable=True,
    )
    op.alter_column(
        "subscriptions",
        "revenuecat_subscriber_id",
        existing_type=sa.String(255),
        nullable=True,
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "provider",
            sa.String(32),
            nullable=False,
            server_default="revenuecat",
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column("provider_customer_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("provider_subscription_id", sa.String(64), nullable=True),
    )
    op.add_column("subscriptions", sa.Column("price_id", sa.String(64), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("scheduled_change_action", sa.String(64), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("scheduled_change_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_subscriptions_provider_subscription_id",
        "subscriptions",
        ["provider_subscription_id"],
    )
    op.create_index(
        "idx_subscriptions_provider_customer",
        "subscriptions",
        ["provider", "provider_customer_id"],
    )
    op.create_index(
        "idx_subscriptions_provider_user_status",
        "subscriptions",
        ["provider", "user_id", "status"],
    )
    op.alter_column("subscriptions", "provider", server_default=None)


def downgrade() -> None:
    """Preserve live billing and fulfillment records on rollback."""
