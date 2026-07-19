from pathlib import Path

MIGRATION = Path("migrations/versions/20260716000001_add_catalog_recipe_tables.py")
REMOVED_MIGRATIONS = (
    Path("migrations/versions/20260716000002_add_meal_recommendation_plan_tables.py"),
    Path("migrations/versions/20260716000003_add_recommendation_swaps_and_interactions.py"),
)


def test_catalog_rework_uses_exactly_four_feature_tables() -> None:
    text = MIGRATION.read_text()

    assert 'op.create_table(\n        "meal_catalog",' in text
    assert 'op.create_table(\n        "meal_catalog_ingredients",' in text
    assert 'op.create_table(\n        "meal_recommendations",' in text
    assert 'op.create_table(\n        "meal_recommendation_operations",' in text
    assert not any(path.exists() for path in REMOVED_MIGRATIONS)


def test_meal_catalog_has_duplicate_guards_and_no_calorie_column() -> None:
    text = MIGRATION.read_text()
    catalog_section = text.split('"meal_catalog_ingredients"')[0]

    assert "uq_meal_catalog_catalog_key" in catalog_section
    assert "uq_meal_catalog_content_hash" in catalog_section
    assert "ck_meal_catalog_has_eligible_meal_type" in catalog_section
    for derived_column in (
        '"servings"',
        '"instructions"',
        '"protein_g"',
        '"carbs_g"',
        '"fat_g"',
        '"fiber_g"',
        '"sugar_g"',
        '"calories"',
    ):
        assert derived_column not in catalog_section


def test_catalog_ingredients_reference_food_reference_authority() -> None:
    text = MIGRATION.read_text()
    ingredient_section = text.split('"meal_catalog_ingredients"')[1].split(
        '"meal_recommendations"'
    )[0]

    assert '"food_reference_id"' in text
    assert 'sa.ForeignKey("food_reference.id", ondelete="RESTRICT")' in text
    assert 'sa.Column("id"' not in ingredient_section
    assert 'sa.Column("position"' not in ingredient_section
    assert "primary_key=True" in ingredient_section


def test_candidate_rows_enforce_selection_owner_and_idempotency_invariants() -> None:
    text = MIGRATION.read_text()

    assert "meal_recommendations" in text
    assert "deferrable=True" in text
    assert "initially=\"DEFERRED\"" in text
    assert "ck_meal_recommendations_anchor_metadata" in text
    assert "uq_meal_recommendations_one_selected" in text
    assert "uq_meal_recommendations_one_active_anchor" in text
    assert "uq_meal_recommendations_anchor_idempotency" in text
    assert "uq_meal_recommendations_logged_meal" in text
    for removed_column in (
        '"shown_at"',
        '"selected_at"',
        '"swapped_at"',
        '"skipped_at"',
        '"target_protein_g"',
        '"target_carbs_g"',
        '"target_fat_g"',
        '"target_fiber_g"',
    ):
        assert removed_column not in text


def test_operation_rows_preserve_request_replay_without_raw_event_table() -> None:
    text = MIGRATION.read_text()

    assert "meal_recommendation_operations" in text
    assert "uq_meal_recommendation_operations_user_type_request" in text
    assert "ck_meal_recommendation_operations_payload" in text
    assert "operation_type IN ('swap', 'log')" in text
    assert '"result_catalog_meal_id"' in text
    for removed_column in (
        '"expected_selection_version"',
        '"requested_catalog_meal_id"',
        '"from_catalog_meal_id"',
        '"to_catalog_meal_id"',
        '"result_status"',
    ):
        assert removed_column not in text
    assert "meal_recommendation_swaps" not in text
    assert "meal_recommendation_interactions" not in text


def test_removed_release_version_terms_do_not_survive_in_migration() -> None:
    text = MIGRATION.read_text()

    stale_terms = (
        "catalog_releases",
        "catalog_recipe_versions",
        "recipe_version_id",
        "catalog_release_id",
        "rights_records",
        "source_revision",
    )
    for term in stale_terms:
        assert term not in text
