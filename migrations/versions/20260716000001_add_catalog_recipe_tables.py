"""Add four-table meal catalog recommendation persistence.

Revision ID: 20260716000001
Revises: 20260707000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260716000001"
down_revision = "20260707000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meal_catalog",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("catalog_key", sa.String(length=160), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("cuisine", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("breakfast_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("lunch_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dinner_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("snack_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint("length(catalog_key) > 0", name="ck_meal_catalog_key"),
        sa.CheckConstraint("length(content_hash) = 64", name="ck_meal_catalog_hash"),
        sa.CheckConstraint("length(name) > 0", name="ck_meal_catalog_name"),
        sa.CheckConstraint("length(cuisine) > 0", name="ck_meal_catalog_cuisine"),
        sa.CheckConstraint(
            "breakfast_eligible OR lunch_eligible OR dinner_eligible OR snack_eligible",
            name="ck_meal_catalog_has_eligible_meal_type",
        ),
        sa.UniqueConstraint("catalog_key", name="uq_meal_catalog_catalog_key"),
        sa.UniqueConstraint("content_hash", name="uq_meal_catalog_content_hash"),
    )
    op.create_index(
        "idx_meal_catalog_active_cuisine",
        "meal_catalog",
        ["is_active", "cuisine"],
    )

    op.create_table(
        "meal_catalog_ingredients",
        sa.Column(
            "catalog_meal_id",
            sa.String(length=36),
            sa.ForeignKey("meal_catalog.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "food_reference_id",
            sa.Integer(),
            sa.ForeignKey("food_reference.id", ondelete="RESTRICT"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_meal_catalog_ingredients_quantity"),
    )
    op.create_index(
        "idx_meal_catalog_ingredients_food_ref",
        "meal_catalog_ingredients",
        ["food_reference_id"],
    )

    op.create_table(
        "meal_recommendations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("slot_id", sa.String(length=36), nullable=False),
        sa.Column("recommendation_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=30), nullable=False),
        sa.Column(
            "catalog_meal_id",
            sa.String(length=36),
            sa.ForeignKey("meal_catalog.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("candidate_rank", sa.Integer(), nullable=False),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score", sa.Numeric(10, 6), nullable=False),
        sa.Column("selection_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "logged_meal_id",
            sa.String(length=36),
            sa.ForeignKey("meal.meal_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_calories", sa.Integer(), nullable=True),
        sa.Column("algorithm_version", sa.String(length=80), nullable=True),
        sa.Column("operation", sa.String(length=40), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["meal_recommendations.id"],
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_meal_recommendations_meal_type",
        ),
        sa.CheckConstraint("candidate_rank >= 0", name="ck_meal_recommendations_rank"),
        sa.CheckConstraint("score >= 0", name="ck_meal_recommendations_score"),
        sa.CheckConstraint(
            "selection_version > 0",
            name="ck_meal_recommendations_selection_version",
        ),
        sa.CheckConstraint(
            "(logged_at IS NULL AND logged_meal_id IS NULL) "
            "OR (logged_at IS NOT NULL AND logged_meal_id IS NOT NULL)",
            name="ck_meal_recommendations_logged_coherent",
        ),
        sa.CheckConstraint(
            "("
            "id = batch_id AND user_id IS NOT NULL AND status IS NOT NULL "
            "AND timezone IS NOT NULL AND start_date IS NOT NULL "
            "AND target_calories IS NOT NULL AND algorithm_version IS NOT NULL "
            "AND operation IS NOT NULL AND idempotency_key IS NOT NULL "
            "AND request_fingerprint IS NOT NULL"
            ") OR ("
            "id <> batch_id AND user_id IS NULL AND status IS NULL "
            "AND timezone IS NULL AND start_date IS NULL "
            "AND target_calories IS NULL AND algorithm_version IS NULL "
            "AND operation IS NULL AND idempotency_key IS NULL "
            "AND request_fingerprint IS NULL AND superseded_at IS NULL"
            ")",
            name="ck_meal_recommendations_anchor_metadata",
        ),
        sa.CheckConstraint(
            "status IS NULL OR status IN ('active', 'superseded', 'failed')",
            name="ck_meal_recommendations_status",
        ),
        sa.CheckConstraint(
            "target_calories IS NULL OR target_calories > 0",
            name="ck_meal_recommendations_target_calories",
        ),
        sa.UniqueConstraint(
            "batch_id",
            "slot_id",
            "candidate_rank",
            name="uq_meal_recommendations_batch_slot_rank",
        ),
        sa.UniqueConstraint(
            "batch_id",
            "slot_id",
            "catalog_meal_id",
            name="uq_meal_recommendations_batch_slot_catalog_meal",
        ),
    )
    op.create_index(
        "idx_meal_recommendations_anchor_user_created",
        "meal_recommendations",
        ["user_id", "created_at"],
        postgresql_where=sa.text("id = batch_id"),
    )
    op.create_index(
        "idx_meal_recommendations_batch_slot",
        "meal_recommendations",
        ["batch_id", "slot_id", "candidate_rank"],
    )
    op.create_index(
        "uq_meal_recommendations_one_selected",
        "meal_recommendations",
        ["batch_id", "slot_id"],
        unique=True,
        postgresql_where=sa.text("is_selected"),
    )
    op.create_index(
        "uq_meal_recommendations_one_active_anchor",
        "meal_recommendations",
        ["user_id", "status"],
        unique=True,
        postgresql_where=sa.text("id = batch_id AND status = 'active'"),
    )
    op.create_index(
        "uq_meal_recommendations_anchor_idempotency",
        "meal_recommendations",
        ["user_id", "operation", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("id = batch_id"),
    )
    op.create_index(
        "uq_meal_recommendations_logged_meal",
        "meal_recommendations",
        ["logged_meal_id"],
        unique=True,
        postgresql_where=sa.text("logged_meal_id IS NOT NULL"),
    )

    op.create_table(
        "meal_recommendation_operations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "batch_id",
            sa.String(length=36),
            sa.ForeignKey("meal_recommendations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slot_id", sa.String(length=36), nullable=False),
        sa.Column("operation_type", sa.String(length=30), nullable=False),
        sa.Column("request_id", sa.String(length=160), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("result_selection_version", sa.Integer(), nullable=True),
        sa.Column(
            "result_catalog_meal_id",
            sa.String(length=36),
            sa.ForeignKey("meal_catalog.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "result_logged_meal_id",
            sa.String(length=36),
            sa.ForeignKey("meal.meal_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "operation_type IN ('swap', 'log')",
            name="ck_meal_recommendation_operations_type",
        ),
        sa.CheckConstraint(
            "length(request_id) BETWEEN 1 AND 160",
            name="ck_meal_recommendation_operations_request_id",
        ),
        sa.CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_meal_recommendation_operations_fingerprint",
        ),
        sa.CheckConstraint(
            "("
            "operation_type = 'swap' AND result_selection_version IS NOT NULL "
            "AND result_catalog_meal_id IS NOT NULL AND result_logged_meal_id IS NULL"
            ") OR ("
            "operation_type = 'log' AND result_logged_meal_id IS NOT NULL "
            "AND result_catalog_meal_id IS NULL"
            ")",
            name="ck_meal_recommendation_operations_payload",
        ),
        sa.UniqueConstraint(
            "user_id",
            "operation_type",
            "request_id",
            name="uq_meal_recommendation_operations_user_type_request",
        ),
    )
    op.create_index(
        "idx_meal_recommendation_operations_batch_slot",
        "meal_recommendation_operations",
        ["batch_id", "slot_id", "created_at"],
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_meal_recommendation_anchor_scope()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            anchor_slot_id text;
            anchor_meal_type text;
            anchor_date date;
        BEGIN
            IF NEW.id = NEW.batch_id THEN
                RETURN NEW;
            END IF;

            SELECT slot_id, meal_type, recommendation_date
            INTO anchor_slot_id, anchor_meal_type, anchor_date
            FROM meal_recommendations
            WHERE id = NEW.batch_id;

            IF anchor_slot_id IS NULL THEN
                RAISE EXCEPTION 'meal recommendation anchor row is missing';
            END IF;

            IF NEW.recommendation_date < anchor_date THEN
                RAISE EXCEPTION 'candidate date cannot precede recommendation batch start';
            END IF;

            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_meal_recommendations_anchor_scope
        BEFORE INSERT OR UPDATE ON meal_recommendations
        FOR EACH ROW
        EXECUTE FUNCTION enforce_meal_recommendation_anchor_scope();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_meal_recommendations_anchor_scope "
        "ON meal_recommendations"
    )
    op.execute("DROP FUNCTION IF EXISTS enforce_meal_recommendation_anchor_scope()")
    op.drop_index(
        "idx_meal_recommendation_operations_batch_slot",
        table_name="meal_recommendation_operations",
    )
    op.drop_table("meal_recommendation_operations")
    op.drop_index("uq_meal_recommendations_logged_meal", table_name="meal_recommendations")
    op.drop_index(
        "uq_meal_recommendations_anchor_idempotency",
        table_name="meal_recommendations",
    )
    op.drop_index(
        "uq_meal_recommendations_one_active_anchor",
        table_name="meal_recommendations",
    )
    op.drop_index("uq_meal_recommendations_one_selected", table_name="meal_recommendations")
    op.drop_index("idx_meal_recommendations_batch_slot", table_name="meal_recommendations")
    op.drop_index(
        "idx_meal_recommendations_anchor_user_created",
        table_name="meal_recommendations",
    )
    op.drop_table("meal_recommendations")
    op.drop_index(
        "idx_meal_catalog_ingredients_food_ref",
        table_name="meal_catalog_ingredients",
    )
    op.drop_table("meal_catalog_ingredients")
    op.drop_index("idx_meal_catalog_active_cuisine", table_name="meal_catalog")
    op.drop_table("meal_catalog")
