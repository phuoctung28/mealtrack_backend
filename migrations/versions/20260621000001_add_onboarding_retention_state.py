"""Add onboarding_retention_states table for D1-D3 campaign tracking.

Revision ID: 20260621000001
Revises: 20260620000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260621000001"
down_revision = "20260620000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_retention_states",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("campaign_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "campaign_timezone",
            sa.String(64),
            nullable=False,
            server_default="UTC",
        ),
        sa.Column("tomorrow_mobility_type", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_onboarding_retention_states_user_id",
        "onboarding_retention_states",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_onboarding_retention_states_user_id",
        table_name="onboarding_retention_states",
    )
    op.drop_table("onboarding_retention_states")
