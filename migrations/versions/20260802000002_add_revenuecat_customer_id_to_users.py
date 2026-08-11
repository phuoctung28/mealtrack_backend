"""Persist the RevenueCat customer used by a completed web claim."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260802000002"
down_revision: str | None = "20260802000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("revenuecat_customer_id", sa.String(length=36), nullable=True),
    )
    op.create_unique_constraint(
        "uq_users_revenuecat_customer_id",
        "users",
        ["revenuecat_customer_id"],
    )
    op.execute(
        sa.text(
            """
            UPDATE web_funnel_outbox
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE job_type = 'revenuecat_association' AND status = 'pending'
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_users_revenuecat_customer_id",
        "users",
        type_="unique",
    )
    op.drop_column("users", "revenuecat_customer_id")
