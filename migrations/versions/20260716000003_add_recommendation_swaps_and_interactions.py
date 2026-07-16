"""Add recommendation swaps and interactions.

Revision ID: 20260716000003
Revises: 20260716000002
"""

import sqlalchemy as sa
from alembic import op

revision = "20260716000003"
down_revision = "20260716000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meal_recommendation_slots",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "meal_recommendation_slots",
        sa.Column("logged_meal_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "meal_recommendation_slots",
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_meal_recommendation_slots_logged_meal",
        "meal_recommendation_slots",
        ["logged_meal_id"],
    )

    op.create_table(
        "meal_recommendation_swaps",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "plan_id",
            sa.String(length=36),
            sa.ForeignKey("meal_recommendation_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "slot_id",
            sa.String(length=36),
            sa.ForeignKey("meal_recommendation_slots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(length=160), nullable=False),
        sa.Column("expected_version", sa.Integer(), nullable=False),
        sa.Column(
            "requested_recipe_version_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "from_recipe_version_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "to_recipe_version_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "expected_version > 0",
            name="ck_meal_recommendation_swaps_expected_version",
        ),
        sa.CheckConstraint(
            "reason IN ('user_requested', 'alternative_selected')",
            name="ck_meal_recommendation_swaps_reason",
        ),
        sa.UniqueConstraint(
            "user_id",
            "request_id",
            name="uq_meal_recommendation_swaps_user_request",
        ),
    )
    op.create_index(
        "idx_meal_recommendation_swaps_slot_created",
        "meal_recommendation_swaps",
        ["slot_id", "created_at"],
    )

    op.create_table(
        "meal_recommendation_interactions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "plan_id",
            sa.String(length=36),
            sa.ForeignKey("meal_recommendation_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "slot_id",
            sa.String(length=36),
            sa.ForeignKey("meal_recommendation_slots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("request_id", sa.String(length=160), nullable=True),
        sa.Column("meal_id", sa.String(length=36), nullable=True),
        sa.Column(
            "recipe_version_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "event_type IN ('swap_selected', 'meal_logged')",
            name="ck_meal_recommendation_interactions_type",
        ),
        sa.UniqueConstraint(
            "slot_id",
            "event_type",
            "request_id",
            name="uq_meal_recommendation_interactions_slot_event_request",
        ),
    )
    op.create_index(
        "idx_meal_recommendation_interactions_plan_created",
        "meal_recommendation_interactions",
        ["plan_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_meal_recommendation_interactions_plan_created",
        table_name="meal_recommendation_interactions",
    )
    op.drop_table("meal_recommendation_interactions")
    op.drop_index(
        "idx_meal_recommendation_swaps_slot_created",
        table_name="meal_recommendation_swaps",
    )
    op.drop_table("meal_recommendation_swaps")
    op.drop_constraint(
        "uq_meal_recommendation_slots_logged_meal",
        "meal_recommendation_slots",
        type_="unique",
    )
    op.drop_column("meal_recommendation_slots", "logged_at")
    op.drop_column("meal_recommendation_slots", "logged_meal_id")
    op.drop_column("meal_recommendation_slots", "version")
