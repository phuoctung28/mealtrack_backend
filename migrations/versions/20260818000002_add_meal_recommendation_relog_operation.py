"""Allow additional catalog meals from an already logged recommendation slot."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260818000002"
down_revision: str | None = "20260818000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TYPE_CONSTRAINT = "ck_meal_recommendation_operations_type"
_PAYLOAD_CONSTRAINT = "ck_meal_recommendation_operations_payload"


def upgrade() -> None:
    op.drop_constraint(
        _TYPE_CONSTRAINT, "meal_recommendation_operations", type_="check"
    )
    op.create_check_constraint(
        _TYPE_CONSTRAINT,
        "meal_recommendation_operations",
        "operation_type IN ('swap', 'log', 'skip', 'relog')",
    )

    op.drop_constraint(
        _PAYLOAD_CONSTRAINT, "meal_recommendation_operations", type_="check"
    )
    op.create_check_constraint(
        _PAYLOAD_CONSTRAINT,
        "meal_recommendation_operations",
        "("
        "operation_type = 'swap' AND result_selection_version IS NOT NULL "
        "AND result_catalog_meal_id IS NOT NULL AND result_logged_meal_id IS NULL"
        ") OR ("
        "operation_type = 'log' AND result_logged_meal_id IS NOT NULL "
        "AND result_catalog_meal_id IS NULL"
        ") OR ("
        "operation_type = 'relog' AND result_logged_meal_id IS NOT NULL "
        "AND result_catalog_meal_id IS NULL"
        ") OR ("
        "operation_type = 'skip' AND result_selection_version IS NULL "
        "AND result_catalog_meal_id IS NULL AND result_logged_meal_id IS NULL"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint(
        _PAYLOAD_CONSTRAINT, "meal_recommendation_operations", type_="check"
    )
    op.create_check_constraint(
        _PAYLOAD_CONSTRAINT,
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

    op.drop_constraint(
        _TYPE_CONSTRAINT, "meal_recommendation_operations", type_="check"
    )
    op.create_check_constraint(
        _TYPE_CONSTRAINT,
        "meal_recommendation_operations",
        "operation_type IN ('swap', 'log', 'skip')",
    )
