"""Add durable_write_records for mutation idempotency replay.

Revision ID: 20260811000001
Revises: 20260807000002
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811000001"
down_revision: str | None = "20260807000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "durable_write_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=False),
        sa.Column("response_body_json", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "action",
            "idempotency_key",
            name="uq_durable_write_user_action_key",
        ),
    )
    op.create_index(
        "ix_durable_write_records_expires_at",
        "durable_write_records",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_durable_write_records_expires_at",
        table_name="durable_write_records",
    )
    op.drop_table("durable_write_records")
