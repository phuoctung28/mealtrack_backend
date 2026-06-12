from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260609000004_normalize_saved_suggestions_and_recipe_steps.py"
)


def test_saved_suggestion_migration_normalizes_children_without_calories() -> None:
    migration_text = MIGRATION_PATH.read_text()

    assert '"saved_suggestion_items"' in migration_text
    assert '"saved_suggestion_steps"' in migration_text
    assert '"meal_instruction_steps"' in migration_text
    assert '"protein_g"' in migration_text
    assert '"carbs_g"' in migration_text
    assert '"fat_g"' in migration_text
    assert '"calories"' not in migration_text


def test_saved_suggestion_migration_keeps_legacy_json_columns() -> None:
    migration_text = MIGRATION_PATH.read_text()

    assert "jsonb_array_elements" in migration_text
    assert "suggestion_data" in migration_text
    assert "m.instructions" in migration_text
    assert 'drop_column("saved_suggestions", "suggestion_data")' not in migration_text
    assert 'drop_column("meal", "instructions")' not in migration_text
