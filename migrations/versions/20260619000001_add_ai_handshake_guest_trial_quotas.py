"""Add ai_handshake_guest_trial_quotas table for one-shot guest parse quota.

Revision ID: 20260619000001
Revises: 20260616000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260619000001"
down_revision = "20260616000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_handshake_guest_trial_quotas",
        sa.Column("install_hash", sa.String(64), primary_key=True, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reserved_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('reserved', 'completed')", name="ck_aihgtq_status"
        ),
    )
    op.create_index(
        "idx_aihgtq_reserved_until",
        "ai_handshake_guest_trial_quotas",
        ["reserved_until"],
    )


def downgrade() -> None:
    op.drop_index("idx_aihgtq_reserved_until", "ai_handshake_guest_trial_quotas")
    op.drop_table("ai_handshake_guest_trial_quotas")
