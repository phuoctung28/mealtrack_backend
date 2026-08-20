"""Add meal_scan_visual_identity for angle-tolerant meal scan reuse.

Revision ID: 20260820000001
Revises: 20260819000001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260820000001"
down_revision: str | None = "20260819000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_scan_visual_identity",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("meal_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("dish_slug", sa.String(length=128), nullable=False),
        sa.Column(
            "ingredients",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("container", sa.String(length=64), nullable=True),
        sa.Column("background", sa.String(length=64), nullable=True),
        sa.Column("identity_key", sa.String(length=255), nullable=False),
        sa.Column(
            "scene_signature",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["meal_id"],
            ["meal.meal_id"],
            name="fk_meal_scan_visual_identity_meal",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_meal_scan_visual_identity_user",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_meal_scan_visual_identity_user_source_dish",
        "meal_scan_visual_identity",
        ["user_id", "source", "dish_slug"],
    )
    op.create_index(
        "ix_meal_scan_visual_identity_user_identity_key",
        "meal_scan_visual_identity",
        ["user_id", "identity_key"],
    )
    op.create_index(
        "ix_meal_scan_visual_identity_meal_id",
        "meal_scan_visual_identity",
        ["meal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meal_scan_visual_identity_meal_id",
        table_name="meal_scan_visual_identity",
    )
    op.drop_index(
        "ix_meal_scan_visual_identity_user_identity_key",
        table_name="meal_scan_visual_identity",
    )
    op.drop_index(
        "ix_meal_scan_visual_identity_user_source_dish",
        table_name="meal_scan_visual_identity",
    )
    op.drop_table("meal_scan_visual_identity")
