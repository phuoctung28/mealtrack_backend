"""Remove retired Paddle fulfillment schema.

Paddle billing is now owned by RevenueCat Web. Legacy Paddle-only subscription
rows cannot satisfy the RevenueCat cache identity invariant and are retired
before the provider columns are removed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801000002"
down_revision: str | None = "20260731121600000000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("LOCK TABLE subscriptions IN ACCESS EXCLUSIVE MODE"))
    op.execute(
        sa.text(
            """
            DELETE FROM subscriptions
            WHERE provider = 'paddle'
              AND user_id IS NULL
              AND revenuecat_subscriber_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM subscriptions WHERE provider = 'paddle') THEN
                    RAISE EXCEPTION
                        'Cannot remove Paddle schema while Paddle subscriptions remain';
                END IF;
            END $$;
            """
        )
    )

    op.drop_index("idx_subscriptions_provider_user_status", table_name="subscriptions")
    op.drop_index("idx_subscriptions_provider_customer", table_name="subscriptions")
    op.drop_constraint(
        "uq_subscriptions_provider_subscription_id",
        "subscriptions",
        type_="unique",
    )
    op.drop_column("subscriptions", "scheduled_change_at")
    op.drop_column("subscriptions", "scheduled_change_action")
    op.drop_column("subscriptions", "price_id")
    op.drop_column("subscriptions", "provider_subscription_id")
    op.drop_column("subscriptions", "provider_customer_id")
    op.drop_column("subscriptions", "provider")
    op.alter_column(
        "subscriptions",
        "revenuecat_subscriber_id",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.alter_column(
        "subscriptions",
        "user_id",
        existing_type=sa.String(36),
        nullable=False,
    )

    op.drop_constraint("uq_users_paddle_customer_id", "users", type_="unique")
    op.drop_column("users", "paddle_customer_id")


def downgrade() -> None:
    """Keep the forward-only removal of retired billing records in place."""
