"""Add affiliate_event_outbox table for durable lifecycle event delivery.

Revision ID: 20260610000001
Revises: 20260609000006
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260610000001"
down_revision = "20260609000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "affiliate_event_outbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("event_id", name="uq_affiliate_event_outbox_event_id"),
    )
    op.create_index(
        "idx_aeo_status_next_attempt",
        "affiliate_event_outbox",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_aeo_status_next_attempt", table_name="affiliate_event_outbox")
    op.drop_table("affiliate_event_outbox")
