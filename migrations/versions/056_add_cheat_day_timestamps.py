"""add cheat_day timestamps

Revision ID: 056
Revises: 055
Create Date: 2026-04-26

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cheat_days", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "cheat_days", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    # Backfill existing rows with marked_at as created_at
    op.execute(
        "UPDATE cheat_days SET created_at = marked_at AT TIME ZONE 'UTC', updated_at = marked_at AT TIME ZONE 'UTC' WHERE created_at IS NULL"
    )
    # Make columns non-nullable
    op.alter_column(
        "cheat_days", "created_at", nullable=False, server_default=sa.text("NOW()")
    )
    op.alter_column(
        "cheat_days", "updated_at", nullable=False, server_default=sa.text("NOW()")
    )


def downgrade() -> None:
    op.drop_column("cheat_days", "updated_at")
    op.drop_column("cheat_days", "created_at")
