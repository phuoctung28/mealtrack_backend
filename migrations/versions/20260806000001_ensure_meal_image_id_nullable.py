"""Ensure meal.image_id is nullable for image-less materialization.

Revision ID: 20260806000001
Revises: 20260804000001

Production evidence (2026-08-06): logging a meal recommendation failed with
`NotNullViolationError` on meal.image_id. Code and migration 20260707000001
already intend nullable image_id; this revision re-applies the alter
idempotently for environments that still have NOT NULL.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260806000001"
down_revision = "20260804000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"]: column for column in inspector.get_columns("meal")}
    image_id = columns.get("image_id")
    if image_id is None:
        return
    if image_id.get("nullable", False):
        return
    op.alter_column(
        "meal",
        "image_id",
        existing_type=sa.String(length=36),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    # Do not re-tighten NOT NULL: historical rows may legitimately have no image.
    pass
