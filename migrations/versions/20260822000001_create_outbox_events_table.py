"""Create outbox_events table for transactional outbox persistence.

Revision ID: 20260822000001
Revises: 20260820000002
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260822000001"
down_revision: str | None = "20260820000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=True),
        sa.Column("aggregate_id", sa.String(length=128), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "next_retry_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "error_log",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
            server_default=sa.text("'[]'::jsonb").with_variant(
                sa.text("'[]'"), "sqlite"
            ),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED_DEAD_LETTER')",
            name="ck_outbox_events_status",
        ),
        sa.CheckConstraint("retry_count >= 0", name="ck_outbox_events_retry_count"),
        sa.CheckConstraint("max_retries >= 0", name="ck_outbox_events_max_retries"),
        sa.UniqueConstraint("event_id", name="uq_outbox_event_id"),
    )

    op.create_index(
        "idx_outbox_claim_due",
        "outbox_events",
        ["status", "next_retry_at"],
    )
    op.create_index(
        "idx_outbox_stale_lease",
        "outbox_events",
        ["status", "lease_expires_at"],
    )
    op.create_index(
        "idx_outbox_cleanup",
        "outbox_events",
        ["status", "updated_at"],
    )
    op.create_index(
        "idx_outbox_aggregate",
        "outbox_events",
        ["aggregate_type", "aggregate_id"],
    )
    op.create_index(
        "idx_outbox_event_type",
        "outbox_events",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_outbox_event_type", table_name="outbox_events")
    op.drop_index("idx_outbox_aggregate", table_name="outbox_events")
    op.drop_index("idx_outbox_cleanup", table_name="outbox_events")
    op.drop_index("idx_outbox_stale_lease", table_name="outbox_events")
    op.drop_index("idx_outbox_claim_due", table_name="outbox_events")
    op.drop_table("outbox_events")
