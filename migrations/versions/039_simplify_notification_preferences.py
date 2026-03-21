"""Simplify notification_preferences: rename progress->daily_summary, drop unused columns.

Revision ID: 039
Revises: 038
Create Date: 2026-03-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "039"
down_revision: Union[str, None] = "038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.scalar() > 0


def upgrade() -> None:
    # 1. Rename progress_notifications_enabled -> daily_summary_enabled
    if _has_column("notification_preferences", "progress_notifications_enabled"):
        op.alter_column(
            "notification_preferences",
            "progress_notifications_enabled",
            new_column_name="daily_summary_enabled",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            existing_server_default=sa.text("1"),
        )

    # 2. Drop unused toggle columns
    for col in [
        "water_reminders_enabled",
        "sleep_reminders_enabled",
        "reengagement_notifications_enabled",
    ]:
        if _has_column("notification_preferences", col):
            op.drop_column("notification_preferences", col)

    # 3. Drop unused time/tracking columns
    for col in [
        "water_reminder_time_minutes",
        "water_reminder_interval_hours",
        "sleep_reminder_time_minutes",
        "last_water_reminder_at",
    ]:
        if _has_column("notification_preferences", col):
            op.drop_column("notification_preferences", col)


def downgrade() -> None:
    # Restore removed time/tracking columns
    if not _has_column("notification_preferences", "last_water_reminder_at"):
        op.add_column(
            "notification_preferences",
            sa.Column("last_water_reminder_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_column("notification_preferences", "sleep_reminder_time_minutes"):
        op.add_column(
            "notification_preferences",
            sa.Column("sleep_reminder_time_minutes", sa.Integer(), nullable=True),
        )
    if not _has_column("notification_preferences", "water_reminder_interval_hours"):
        op.add_column(
            "notification_preferences",
            sa.Column("water_reminder_interval_hours", sa.Integer(), nullable=False, server_default="2"),
        )
    if not _has_column("notification_preferences", "water_reminder_time_minutes"):
        op.add_column(
            "notification_preferences",
            sa.Column("water_reminder_time_minutes", sa.Integer(), nullable=True, server_default="960"),
        )

    # Restore removed toggle columns
    for col, default in [
        ("reengagement_notifications_enabled", "1"),
        ("sleep_reminders_enabled", "1"),
        ("water_reminders_enabled", "1"),
    ]:
        if not _has_column("notification_preferences", col):
            op.add_column(
                "notification_preferences",
                sa.Column(col, sa.Boolean(), nullable=False, server_default=sa.text(default)),
            )

    # Rename daily_summary_enabled back to progress_notifications_enabled
    if _has_column("notification_preferences", "daily_summary_enabled"):
        op.alter_column(
            "notification_preferences",
            "daily_summary_enabled",
            new_column_name="progress_notifications_enabled",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            existing_server_default=sa.text("1"),
        )
