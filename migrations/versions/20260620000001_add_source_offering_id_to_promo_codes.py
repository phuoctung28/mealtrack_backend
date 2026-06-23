"""Add source_offering_id to promo_codes — restricts a code to a specific RC offering.

Revision ID: 20260620000001
Revises: 20260619000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260620000001"
down_revision = "20260619000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "promo_codes",
        sa.Column("source_offering_id", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("promo_codes", "source_offering_id")
