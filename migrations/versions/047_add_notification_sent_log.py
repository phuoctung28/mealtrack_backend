"""Add notification_sent_log table for cross-worker deduplication.

Revision ID: 047
Revises: 046
"""
from alembic import op
import sqlalchemy as sa

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_sent_log",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("sent_minute", sa.String(16), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", "notification_type", "sent_minute"),
    )
    op.create_index(
        "ix_sent_log_cleanup", "notification_sent_log", ["sent_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_sent_log_cleanup", table_name="notification_sent_log")
    op.drop_table("notification_sent_log")
