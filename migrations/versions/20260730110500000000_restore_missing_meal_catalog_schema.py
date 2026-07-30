"""Restore catalog tables skipped by a legacy Alembic revision collision.

The original catalog branch shares history with a revision identifier that was
also used by the body-fat branch. Legacy deployments can therefore reach the
merged head without creating any catalog tables. This is deliberately a
forward-only repair: it preserves existing catalog data and only reconstructs
the schema when every catalog table is absent.
"""

import importlib.util
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "20260730110500000000"
down_revision: str | None = "20260730102158384558"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATALOG_TABLES = frozenset(
    {
        "meal_catalog",
        "meal_catalog_ingredients",
        "meal_recommendations",
        "meal_recommendation_operations",
    }
)


def _run_catalog_baseline_upgrade() -> None:
    """Run the immutable catalog baseline only for an entirely absent schema."""
    baseline_path = Path(__file__).with_name(
        "20260716000001_add_catalog_recipe_tables.py"
    )
    spec = importlib.util.spec_from_file_location(
        "catalog_recipe_tables_baseline", baseline_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Catalog baseline migration could not be loaded")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.upgrade()


def _add_catalog_branch_follow_up_schema() -> None:
    """Apply the additive catalog-branch migrations skipped with the baseline."""
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
    op.add_column(
        "meal_recommendations",
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "meal_recommendations",
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE meal_recommendations SET seen_at = COALESCE(seen_at, created_at) "
        "WHERE is_selected = TRUE"
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


def _ensure_food_reference_search_index(inspector: sa.Inspector) -> None:
    if not inspector.has_table("food_reference"):
        return

    columns = {column["name"] for column in inspector.get_columns("food_reference")}
    if "name_normalized" not in columns:
        raise RuntimeError("food_reference.name_normalized is required for catalog search")

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_food_reference_name_normalized_trgm "
        "ON food_reference USING gin (name_normalized gin_trgm_ops)"
    )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = {
        table_name for table_name in CATALOG_TABLES if inspector.has_table(table_name)
    }

    if existing_tables and existing_tables != CATALOG_TABLES:
        missing_tables = ", ".join(sorted(CATALOG_TABLES - existing_tables))
        raise RuntimeError(
            "Catalog schema is partially present; refusing automatic repair. "
            f"Missing tables: {missing_tables}"
        )

    if not existing_tables:
        _run_catalog_baseline_upgrade()
        _add_catalog_branch_follow_up_schema()

    _ensure_food_reference_search_index(inspector)


def downgrade() -> None:
    """Keep the forward repair schema intact if a release is rolled back."""
