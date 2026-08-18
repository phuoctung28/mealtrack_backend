"""Widen users.provider so EMAIL_LINK and ANONYMOUS persist.

Production evidence (2026-08-18): POST /v1/users/sync failed with
`StringDataRightTruncationError: value too long for type character varying(6)`
while writing provider='EMAIL_LINK'. native_enum=False VARCHAR length defaulted
to 6 for the original GOOGLE/APPLE names.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260818000002"
down_revision = "20260818000001"
branch_labels = None
depends_on = None

PROVIDER_LENGTH = 32


def upgrade() -> None:
    """Widen provider to VARCHAR(32), including native-enum leftovers."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return
    columns = {column["name"]: column for column in inspector.get_columns("users")}
    provider = columns.get("provider")
    if provider is None:
        return
    current_length = getattr(provider["type"], "length", None)
    if current_length is not None and current_length >= PROVIDER_LENGTH:
        return
    op.execute(
        sa.text(
            "ALTER TABLE users ALTER COLUMN provider TYPE VARCHAR(32) "
            "USING provider::text"
        )
    )


def downgrade() -> None:
    """Keep the wider provider column; truncating would break EMAIL_LINK rows."""
