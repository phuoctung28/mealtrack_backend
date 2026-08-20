"""Widen mealimage.url so Cloudinary / CDN URLs are not truncated.

Revision ID: 20260820000002
Revises: 20260819000001
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820000002"
down_revision: str | None = "20260819000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "mealimage",
        "url",
        existing_type=sa.String(length=255),
        type_=sa.String(length=1024),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "mealimage",
        "url",
        existing_type=sa.String(length=1024),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
