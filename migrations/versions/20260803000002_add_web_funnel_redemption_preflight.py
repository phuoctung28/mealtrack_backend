"""Add opaque preflight state for web-funnel redemptions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260803000002"
down_revision: str | None = "20260803000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("web_funnel_redemptions", sa.Column("preflight_token_hash", sa.String(64)))
    op.add_column("web_funnel_redemptions", sa.Column("preflight_token_expires_at", sa.DateTime(timezone=True)))
    op.add_column("web_funnel_redemptions", sa.Column("preflight_uid", sa.String(128)))
    op.add_column("web_funnel_redemptions", sa.Column("preflight_at", sa.DateTime(timezone=True)))
    op.create_unique_constraint("uq_web_funnel_redemptions_preflight_token", "web_funnel_redemptions", ["preflight_token_hash"])


def downgrade() -> None:
    raise NotImplementedError("This migration is forward-only to protect redemption ownership.")
