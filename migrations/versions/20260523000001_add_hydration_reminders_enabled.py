"""Add hydration_reminders_enabled to notification_preferences.

Revision ID: 20260523000001
Revises: 20260522100001
"""
import sqlalchemy as sa
from alembic import op

revision = "20260523000001"
down_revision = "20260522100001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_preferences",
        sa.Column(
            "hydration_reminders_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )


def downgrade() -> None:
    op.drop_column("notification_preferences", "hydration_reminders_enabled")
