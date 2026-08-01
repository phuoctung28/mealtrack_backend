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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    subscription_columns = {
        column["name"] for column in inspector.get_columns("subscriptions")
    }

    if "provider" in subscription_columns:
        # Serialize the verification and deletion with incoming subscription writes.
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

        subscription_indexes = {
            index["name"] for index in inspector.get_indexes("subscriptions")
        }
        for index_name in (
            "idx_subscriptions_provider_user_status",
            "idx_subscriptions_provider_customer",
        ):
            if index_name in subscription_indexes:
                op.drop_index(index_name, table_name="subscriptions")

        subscription_constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("subscriptions")
        }
        if "uq_subscriptions_provider_subscription_id" in subscription_constraints:
            op.drop_constraint(
                "uq_subscriptions_provider_subscription_id",
                "subscriptions",
                type_="unique",
            )

        for column_name in (
            "scheduled_change_at",
            "scheduled_change_action",
            "price_id",
            "provider_subscription_id",
            "provider_customer_id",
            "provider",
        ):
            if column_name in subscription_columns:
                op.drop_column("subscriptions", column_name)

    if "revenuecat_subscriber_id" in subscription_columns:
        op.alter_column(
            "subscriptions",
            "revenuecat_subscriber_id",
            existing_type=sa.String(255),
            nullable=False,
        )
    if "user_id" in subscription_columns:
        op.alter_column(
            "subscriptions",
            "user_id",
            existing_type=sa.String(36),
            nullable=False,
        )

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "paddle_customer_id" in user_columns:
        user_constraints = {
            constraint["name"] for constraint in inspector.get_unique_constraints("users")
        }
        if "uq_users_paddle_customer_id" in user_constraints:
            op.drop_constraint("uq_users_paddle_customer_id", "users", type_="unique")
        op.drop_column("users", "paddle_customer_id")


def downgrade() -> None:
    """Keep the forward-only removal of retired billing records in place."""
