"""Add skip and shown state to meal recommendations.

Revision ID: 20260724000001
Revises: 20260723000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260724000001"
down_revision = "20260723000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meal_recommendations",
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "meal_recommendations",
        sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_meal_recommendations_skip_terminal",
        "meal_recommendations",
        "skipped_at IS NULL OR (logged_at IS NULL AND logged_meal_id IS NULL)",
    )

    op.drop_constraint(
        "ck_meal_recommendation_operations_type",
        "meal_recommendation_operations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_meal_recommendation_operations_type",
        "meal_recommendation_operations",
        "operation_type IN ('swap', 'log', 'skip')",
    )

    op.drop_constraint(
        "ck_meal_recommendation_operations_payload",
        "meal_recommendation_operations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_meal_recommendation_operations_payload",
        "meal_recommendation_operations",
        "("
        "operation_type = 'swap' AND result_selection_version IS NOT NULL "
        "AND result_catalog_meal_id IS NOT NULL AND result_logged_meal_id IS NULL"
        ") OR ("
        "operation_type = 'log' AND result_logged_meal_id IS NOT NULL "
        "AND result_catalog_meal_id IS NULL"
        ") OR ("
        "operation_type = 'skip' AND result_selection_version IS NULL "
        "AND result_catalog_meal_id IS NULL AND result_logged_meal_id IS NULL"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_meal_recommendation_operations_payload",
        "meal_recommendation_operations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_meal_recommendation_operations_payload",
        "meal_recommendation_operations",
        "("
        "operation_type = 'swap' AND result_selection_version IS NOT NULL "
        "AND result_catalog_meal_id IS NOT NULL AND result_logged_meal_id IS NULL"
        ") OR ("
        "operation_type = 'log' AND result_logged_meal_id IS NOT NULL "
        "AND result_catalog_meal_id IS NULL"
        ")",
    )

    op.drop_constraint(
        "ck_meal_recommendation_operations_type",
        "meal_recommendation_operations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_meal_recommendation_operations_type",
        "meal_recommendation_operations",
        "operation_type IN ('swap', 'log')",
    )

    op.drop_constraint(
        "ck_meal_recommendations_skip_terminal",
        "meal_recommendations",
        type_="check",
    )
    op.drop_column("meal_recommendations", "skipped_at")
    op.drop_column("meal_recommendations", "shown_at")
