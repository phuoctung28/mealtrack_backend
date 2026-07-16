"""Add durable meal recommendation plan tables.

Revision ID: 20260716000002
Revises: 20260716000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260716000002"
down_revision = "20260716000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meal_recommendation_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("daily_calories", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=80), nullable=False),
        sa.Column(
            "catalog_release_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_releases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("allergy_evaluated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded', 'failed')",
            name="ck_meal_recommendation_plans_status",
        ),
        sa.CheckConstraint(
            "daily_calories > 0",
            name="ck_meal_recommendation_plans_daily_calories",
        ),
        sa.CheckConstraint(
            "length(idempotency_key) BETWEEN 1 AND 160",
            name="ck_meal_recommendation_plans_idempotency_key",
        ),
        sa.UniqueConstraint(
            "user_id",
            "operation",
            "idempotency_key",
            name="uq_meal_recommendation_plans_user_idempotency",
        ),
    )
    op.create_index(
        "idx_meal_recommendation_plans_user_created",
        "meal_recommendation_plans",
        ["user_id", "created_at"],
    )
    op.create_index(
        "uq_meal_recommendation_plans_one_active",
        "meal_recommendation_plans",
        ["user_id", "status"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "meal_recommendation_slots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "plan_id",
            sa.String(length=36),
            sa.ForeignKey("meal_recommendation_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slot_date", sa.Date(), nullable=False),
        sa.Column("day_index", sa.Integer(), nullable=False),
        sa.Column("meal_type", sa.String(length=30), nullable=False),
        sa.Column(
            "recipe_version_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("target_calories", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("day_index BETWEEN 0 AND 2", name="ck_meal_rec_slots_day"),
        sa.CheckConstraint("target_calories > 0", name="ck_meal_rec_slots_target"),
        sa.UniqueConstraint(
            "plan_id",
            "slot_date",
            "meal_type",
            name="uq_meal_recommendation_slots_plan_date_type",
        ),
        sa.UniqueConstraint(
            "plan_id",
            "recipe_version_id",
            name="uq_meal_recommendation_slots_unique_recipe",
        ),
    )
    op.create_index(
        "idx_meal_recommendation_slots_plan_position",
        "meal_recommendation_slots",
        ["plan_id", "position"],
    )

    op.create_table(
        "meal_recommendation_slot_alternatives",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "slot_id",
            sa.String(length=36),
            sa.ForeignKey("meal_recommendation_slots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recipe_version_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("target_calories", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "target_calories > 0",
            name="ck_meal_rec_alternatives_target",
        ),
        sa.UniqueConstraint(
            "slot_id",
            "position",
            name="uq_meal_recommendation_alternatives_slot_position",
        ),
        sa.UniqueConstraint(
            "slot_id",
            "recipe_version_id",
            name="uq_meal_recommendation_alternatives_slot_recipe",
        ),
    )
    op.create_index(
        "idx_meal_recommendation_alternatives_slot_position",
        "meal_recommendation_slot_alternatives",
        ["slot_id", "position"],
    )


def downgrade() -> None:
    op.drop_table("meal_recommendation_slot_alternatives")
    op.drop_table("meal_recommendation_slots")
    op.drop_index(
        "uq_meal_recommendation_plans_one_active",
        table_name="meal_recommendation_plans",
    )
    op.drop_table("meal_recommendation_plans")
