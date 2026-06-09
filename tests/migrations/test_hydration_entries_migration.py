from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260609000003_add_hydration_entries.py"
)


def test_hydration_entries_migration_stores_macros_not_calorie_aliases() -> None:
    migration_text = MIGRATION_PATH.read_text()

    assert '"protein_g"' in migration_text
    assert '"carbs_g"' in migration_text
    assert '"fat_g"' in migration_text
    assert '"fiber_g"' in migration_text
    assert '"sugar_g"' in migration_text
    assert '"kcal"' not in migration_text
    assert '"calories"' not in migration_text


def test_hydration_entries_migration_backfills_legacy_meals() -> None:
    migration_text = MIGRATION_PATH.read_text()

    assert "legacy_meal_id" in migration_text
    assert "meal.meal_type = 'hydration' OR meal.source = 'hydration'" in migration_text
    assert "ON CONFLICT (legacy_meal_id) DO NOTHING" in migration_text
