"""Add normalized hydration entries.

Revision ID: 20260609000003
Revises: 20260609000002
"""

import sqlalchemy as sa
from alembic import op

revision = "20260609000003"
down_revision = "20260609000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hydration_entries",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("drink_id", sa.String(64), nullable=True),
        sa.Column("drink_name_snapshot", sa.String(255), nullable=False),
        sa.Column("emoji_snapshot", sa.String(16), nullable=True),
        sa.Column("volume_ml", sa.Integer, nullable=False),
        sa.Column("credited_ml", sa.Integer, nullable=False),
        sa.Column("protein_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("carbs_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("fat_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("fiber_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("sugar_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="hydration"),
        sa.Column(
            "legacy_meal_id",
            sa.String(36),
            sa.ForeignKey("meal.meal_id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
    )
    op.create_index("ix_hydration_entries_user_id", "hydration_entries", ["user_id"])
    op.create_index("ix_hydration_entries_drink_id", "hydration_entries", ["drink_id"])
    op.create_index(
        "idx_hydration_entries_user_logged_at",
        "hydration_entries",
        ["user_id", "logged_at"],
    )

    op.execute("""
        INSERT INTO hydration_entries (
            id,
            user_id,
            drink_id,
            drink_name_snapshot,
            emoji_snapshot,
            volume_ml,
            credited_ml,
            protein_g,
            carbs_g,
            fat_g,
            fiber_g,
            sugar_g,
            logged_at,
            source,
            legacy_meal_id,
            created_at,
            updated_at
        )
        SELECT
            'hydr_' || replace(meal.meal_id, '-', ''),
            meal.user_id,
            NULL,
            coalesce(meal.dish_name, 'Water'),
            meal.emoji,
            coalesce(meal.quantity, 0),
            coalesce(meal.quantity, 0),
            coalesce(nutrition.protein, 0),
            coalesce(nutrition.carbs, 0),
            coalesce(nutrition.fat, 0),
            coalesce(nutrition.fiber, 0),
            coalesce(nutrition.sugar, 0),
            coalesce(meal.created_at, meal.ready_at, now()),
            coalesce(meal.source, 'hydration'),
            meal.meal_id,
            now(),
            now()
        FROM meal
        LEFT JOIN nutrition ON nutrition.meal_id = meal.meal_id
        WHERE (meal.meal_type = 'hydration' OR meal.source = 'hydration')
          AND meal.status != 'INACTIVE'
        ON CONFLICT (legacy_meal_id) DO NOTHING
        """)


def downgrade() -> None:
    op.drop_index(
        "idx_hydration_entries_user_logged_at",
        table_name="hydration_entries",
    )
    op.drop_index("ix_hydration_entries_drink_id", table_name="hydration_entries")
    op.drop_index("ix_hydration_entries_user_id", table_name="hydration_entries")
    op.drop_table("hydration_entries")
