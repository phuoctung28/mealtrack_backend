"""Add normalized read-path indexes.

Revision ID: 20260609000006
Revises: 20260609000005
"""

import sqlalchemy as sa
from alembic import op

revision = "20260609000006"
down_revision = "20260609000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_user_fcm_tokens_user_active",
        "user_fcm_tokens",
        ["user_id", "is_active"],
    )
    op.create_index(
        "idx_notifications_user_status_date",
        "notifications",
        ["user_id", "status", "scheduled_date"],
    )
    op.create_index(
        "idx_notifications_processing_reclaim",
        "notifications",
        ["scheduled_for_utc"],
        postgresql_where=sa.text("status = 'processing'"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_notifications_processing_reclaim",
        table_name="notifications",
    )
    op.drop_index(
        "idx_notifications_user_status_date",
        table_name="notifications",
    )
    op.drop_index(
        "idx_user_fcm_tokens_user_active",
        table_name="user_fcm_tokens",
    )
