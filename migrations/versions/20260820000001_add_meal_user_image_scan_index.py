"""Add index for user meal scan cache lookups by image_id.

Revision ID: 20260820000001
Revises: 20260819000001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820000001"
down_revision: str | None = "20260819000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_meal_user_image_source",
        "meal",
        ["user_id", "image_id", "source"],
        postgresql_where=sa.text("image_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_meal_user_image_source", table_name="meal")
