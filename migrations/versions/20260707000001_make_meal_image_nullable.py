"""Make meal image optional.

Revision ID: 20260707000001
Revises: 20260705000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260707000001"
down_revision = "20260705000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "meal",
        "image_id",
        existing_type=sa.String(length=36),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "meal",
        "image_id",
        existing_type=sa.String(length=36),
        nullable=False,
        existing_nullable=True,
    )
