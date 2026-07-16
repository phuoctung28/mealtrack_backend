from pathlib import Path

MIGRATION = Path("migrations/versions/20260716000001_add_catalog_recipe_tables.py")
PLAN_MIGRATION = Path(
    "migrations/versions/20260716000002_add_meal_recommendation_plan_tables.py"
)


def test_catalog_recipe_migration_enforces_active_release_and_immutability() -> None:
    text = MIGRATION.read_text()

    assert "uq_catalog_releases_single_active" in text
    assert "prevent_catalog_published_version_mutation" in text
    assert "prevent_catalog_published_child_mutation" in text


def test_catalog_recipe_migration_requires_rights_before_publish() -> None:
    text = MIGRATION.read_text()

    assert "require_catalog_approved_rights_before_publish" in text
    assert "published catalog recipe versions require approved rights" in text
    assert "rights.status = 'approved'" in text


def test_meal_recommendation_plan_migration_has_idempotency_and_active_guard() -> None:
    text = PLAN_MIGRATION.read_text()

    assert "uq_meal_recommendation_plans_user_idempotency" in text
    assert 'sa.Column("operation", sa.String(length=40), nullable=False)' in text
    assert '"operation",' in text
    assert "uq_meal_recommendation_plans_one_active" in text
    assert "meal_recommendation_slot_alternatives" in text
