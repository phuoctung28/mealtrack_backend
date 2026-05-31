"""Create Crave swipe engine tables.

Revision ID: 20260529000001
Revises: 20260525000003
Create Date: 2026-05-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260529000001"
down_revision: str | Sequence[str] | None = "20260525000003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "meal_catalog",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("meal_name", sa.String(length=255), nullable=False),
        sa.Column("english_name", sa.String(length=255), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Float(), nullable=False),
        sa.Column("carbs_g", sa.Float(), nullable=False),
        sa.Column("fat_g", sa.Float(), nullable=False),
        sa.Column("fiber_g", sa.Float(), nullable=False),
        sa.Column("calorie_band", sa.Integer(), nullable=False),
        sa.Column("cuisine", sa.String(length=64), nullable=True),
        sa.Column("meal_types", sa.JSON(), nullable=False),
        sa.Column("ingredients", sa.JSON(), nullable=False),
        sa.Column("recipe_steps", sa.JSON(), nullable=True),
        sa.Column("recipe_status", sa.String(length=16), nullable=False),
        sa.Column("prep_time_minutes", sa.Integer(), nullable=True),
        sa.Column("dietary_flags", sa.JSON(), nullable=False),
        sa.Column("allergen_flags", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=1024), nullable=True),
        sa.Column("image_status", sa.String(length=16), nullable=False),
        sa.Column("embedding", Vector(512), nullable=True),
        sa.Column("times_shown", sa.Integer(), nullable=False),
        sa.Column("times_saved", sa.Integer(), nullable=False),
        sa.Column("times_cooked", sa.Integer(), nullable=False),
        sa.Column("times_skipped", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meal_catalog_band_status",
        "meal_catalog",
        ["calorie_band", "status"],
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_meal_catalog_embedding "
        "ON meal_catalog USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_meal_catalog_dietary "
        "ON meal_catalog USING gin ((dietary_flags::jsonb))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_meal_catalog_allergen "
        "ON meal_catalog USING gin ((allergen_flags::jsonb))"
    )

    op.create_table(
        "user_taste_profile",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("cuisine_affinity", sa.JSON(), nullable=False),
        sa.Column("ingredient_affinity", sa.JSON(), nullable=False),
        sa.Column("tag_affinity", sa.JSON(), nullable=False),
        sa.Column("macro_shape_pref", sa.JSON(), nullable=False),
        sa.Column("taste_embedding", Vector(512), nullable=True),
        sa.Column("swipe_count", sa.Integer(), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "crave_swipe_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("catalog_meal_id", sa.String(length=36), nullable=False),
        sa.Column("deck_id", sa.String(length=36), nullable=True),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("dwell_ms", sa.Integer(), nullable=True),
        sa.Column("meal_type", sa.String(length=20), nullable=True),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crave_swipe_user_created",
        "crave_swipe_events",
        ["user_id", "created_at"],
    )
    op.create_index("ix_crave_swipe_meal", "crave_swipe_events", ["catalog_meal_id"])

    op.create_table(
        "crave_seen",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("catalog_meal_id", sa.String(length=36), nullable=False),
        sa.Column("seen_count", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "catalog_meal_id"),
        sa.UniqueConstraint(
            "user_id", "catalog_meal_id", name="uq_crave_seen_user_meal"
        ),
    )

    op.add_column(
        "saved_suggestions",
        sa.Column("catalog_meal_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "saved_suggestions",
        sa.Column(
            "source",
            sa.String(length=24),
            nullable=False,
            server_default="suggestion",
        ),
    )
    op.alter_column("saved_suggestions", "source", server_default=None)


def downgrade() -> None:
    op.drop_column("saved_suggestions", "source")
    op.drop_column("saved_suggestions", "catalog_meal_id")
    op.drop_table("crave_seen")
    op.drop_index("ix_crave_swipe_meal", table_name="crave_swipe_events")
    op.drop_index("ix_crave_swipe_user_created", table_name="crave_swipe_events")
    op.drop_table("crave_swipe_events")
    op.drop_table("user_taste_profile")
    op.execute("DROP INDEX IF EXISTS ix_meal_catalog_allergen")
    op.execute("DROP INDEX IF EXISTS ix_meal_catalog_dietary")
    op.execute("DROP INDEX IF EXISTS ix_meal_catalog_embedding")
    op.drop_index("ix_meal_catalog_band_status", table_name="meal_catalog")
    op.drop_table("meal_catalog")
