"""Add provider-neutral subscription fields.

Revision ID: 20260726000003
Revises: 20260726000002
"""

import sqlalchemy as sa
from alembic import op

revision = "20260726000003"
down_revision = "20260726000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("provider", sa.String(length=32), nullable=False, server_default="revenuecat"))
    op.add_column("subscriptions", sa.Column("provider_customer_id", sa.String(length=255), nullable=True))
    op.add_column("subscriptions", sa.Column("provider_subscription_id", sa.String(length=255), nullable=True))
    op.add_column("subscriptions", sa.Column("provider_transaction_id", sa.String(length=255), nullable=True))
    op.add_column("subscriptions", sa.Column("source_checkout_id", sa.String(length=36), nullable=True))
    op.alter_column("subscriptions", "revenuecat_subscriber_id", existing_type=sa.String(length=255), nullable=True)
    op.create_foreign_key(
        "fk_subscriptions_source_checkout_id_web_funnel_checkouts",
        "subscriptions",
        "web_funnel_checkouts",
        ["source_checkout_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_subscriptions_provider_subscription",
        "subscriptions",
        ["provider", "provider_subscription_id"],
    )
    op.create_check_constraint(
        "ck_subscriptions_provider_identifiers",
        "subscriptions",
        "(provider = 'revenuecat' AND revenuecat_subscriber_id IS NOT NULL) OR "
        "(provider <> 'revenuecat' AND provider_subscription_id IS NOT NULL)",
    )
    op.create_index("idx_subscriptions_provider_user_status", "subscriptions", ["provider", "user_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_subscriptions_provider_user_status", table_name="subscriptions")
    op.drop_constraint("ck_subscriptions_provider_identifiers", "subscriptions", type_="check")
    op.drop_constraint("uq_subscriptions_provider_subscription", "subscriptions", type_="unique")
    op.drop_constraint("fk_subscriptions_source_checkout_id_web_funnel_checkouts", "subscriptions", type_="foreignkey")
    op.alter_column("subscriptions", "revenuecat_subscriber_id", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("subscriptions", "source_checkout_id")
    op.drop_column("subscriptions", "provider_transaction_id")
    op.drop_column("subscriptions", "provider_subscription_id")
    op.drop_column("subscriptions", "provider_customer_id")
    op.drop_column("subscriptions", "provider")
