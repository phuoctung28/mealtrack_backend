"""Add image_url to hydration_entries for beverage scan.

Revision ID: 20260616000001
Revises: 20260610000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260616000001"
down_revision = "20260610000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hydration_entries",
        sa.Column("image_url", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hydration_entries", "image_url")
