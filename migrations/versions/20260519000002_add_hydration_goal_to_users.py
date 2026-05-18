"""Add hydration_goal_ml column to users table.

Revision ID: 20260519000002
Revises: 20260519000001

Default 2000 ml covers the standard WHO recommendation for most adults.
Application-enforced bounds: 500–4000 ml (validated at API layer).
Existing rows are backfilled to 2000 via server_default.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260519000002"
down_revision = "20260519000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "hydration_goal_ml",
            sa.Integer,
            nullable=False,
            server_default="2000",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "hydration_goal_ml")
