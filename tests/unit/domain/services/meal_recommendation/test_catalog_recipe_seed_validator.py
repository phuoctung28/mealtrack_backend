from src.domain.services.meal_recommendation.catalog_recipe_seed_validator import (
    validate_catalog_seed_manifest,
)


def _recipe(
    recipe_key: str,
    cuisine: str,
    meal_type: str,
    *,
    rights_status: str = "approved",
    source_type: str = "commissioned",
    fiber_g: float = 0.4,
    carbs_g: float = 28.0,
) -> dict:
    return {
        "recipe_key": recipe_key,
        "cuisine": cuisine,
        "name": f"{cuisine} {meal_type}",
        "meal_types": [meal_type],
        "rights": {
            "status": rights_status,
            "approver": "content-review",
            "agreement_identifier": f"agreement-{recipe_key}",
        },
        "sources": [{"source_type": source_type}],
        "ingredients": [
            {
                "food_reference_id": 7,
                "name": "Rice",
                "quantity": 100,
                "unit": "g",
                "resolved_grams": 100,
                "protein_g": 2.7,
                "carbs_g": carbs_g,
                "fat_g": 0.3,
                "fiber_g": fiber_g,
                "sugar_g": 0.1,
            }
        ],
    }


def _complete_manifest() -> dict:
    recipes = []
    for cuisine in ("vietnamese", "japanese", "korean"):
        for meal_type in ("breakfast", "lunch", "dinner"):
            recipes.append(_recipe(f"{cuisine}-{meal_type}", cuisine, meal_type))
    return {
        "release_key": "test-release",
        "expected_recipe_count": len(recipes),
        "recipes": recipes,
    }


def test_valid_manifest_reports_digest_and_coverage():
    manifest = _complete_manifest()

    result = validate_catalog_seed_manifest(
        manifest,
        expected_recipe_count=9,
        min_per_cuisine_meal_type=1,
        expected_cuisine_counts={
            "vietnamese": 3,
            "japanese": 3,
            "korean": 3,
        },
    )

    assert result.is_valid is True
    assert len(result.manifest_digest) == 64
    assert result.recipe_count == 9
    assert result.coverage["vietnamese"]["breakfast"] == 1


def test_manifest_rejects_wrong_recipe_count_and_coverage():
    manifest = {
        "release_key": "test-release",
        "expected_recipe_count": 180,
        "recipes": [_recipe("vn-breakfast", "vietnamese", "breakfast")],
    }

    result = validate_catalog_seed_manifest(manifest)

    assert result.is_valid is False
    assert "recipe count must be 180, got 1" in result.errors
    assert "cuisine japanese requires 60 recipes, got 0" in result.errors
    assert any("coverage japanese/lunch" in error for error in result.errors)


def test_manifest_rejects_unapproved_rights_and_unapproved_source():
    manifest = {
        "release_key": "test-release",
        "expected_recipe_count": 1,
        "recipes": [
            _recipe(
                "vn-breakfast",
                "vietnamese",
                "breakfast",
                rights_status="pending",
                source_type="web_scrape",
            )
        ],
    }

    result = validate_catalog_seed_manifest(
        manifest,
        expected_recipe_count=1,
        min_per_cuisine_meal_type=0,
        expected_cuisine_counts=None,
    )

    assert result.is_valid is False
    assert "recipes[0].rights.status must be approved" in result.errors
    assert any("source_type is not allowlisted" in error for error in result.errors)


def test_manifest_rejects_unresolved_nutritional_ingredient():
    manifest = {
        "release_key": "test-release",
        "expected_recipe_count": 1,
        "recipes": [_recipe("vn-breakfast", "vietnamese", "breakfast")],
    }
    del manifest["recipes"][0]["ingredients"][0]["food_reference_id"]

    result = validate_catalog_seed_manifest(
        manifest,
        expected_recipe_count=1,
        min_per_cuisine_meal_type=0,
        expected_cuisine_counts=None,
    )

    assert result.is_valid is False
    assert any("food_reference_id is required" in error for error in result.errors)


def test_manifest_rejects_display_only_ingredient_without_db_required_fields():
    manifest = {
        "release_key": "test-release",
        "expected_recipe_count": 1,
        "recipes": [_recipe("vn-breakfast", "vietnamese", "breakfast")],
    }
    ingredient = manifest["recipes"][0]["ingredients"][0]
    ingredient["is_display_only"] = True
    del ingredient["food_reference_id"]

    result = validate_catalog_seed_manifest(
        manifest,
        expected_recipe_count=1,
        min_per_cuisine_meal_type=0,
        expected_cuisine_counts=None,
    )

    assert result.is_valid is False
    assert any("food_reference_id is required" in error for error in result.errors)


def test_manifest_rejects_fiber_above_carbs():
    manifest = {
        "release_key": "test-release",
        "expected_recipe_count": 1,
        "recipes": [
            _recipe(
                "vn-breakfast",
                "vietnamese",
                "breakfast",
                fiber_g=4.0,
                carbs_g=2.0,
            )
        ],
    }

    result = validate_catalog_seed_manifest(
        manifest,
        expected_recipe_count=1,
        min_per_cuisine_meal_type=0,
        expected_cuisine_counts=None,
    )

    assert result.is_valid is False
    assert any("fiber_g exceeds carbs_g" in error for error in result.errors)


def test_manifest_rejects_recipe_macro_totals_that_do_not_match_ingredients():
    recipe = _recipe("vn-breakfast", "vietnamese", "breakfast")
    recipe["protein_g"] = 99
    recipe["calories"] = 999
    manifest = {
        "release_key": "test-release",
        "expected_recipe_count": 1,
        "recipes": [recipe],
    }

    result = validate_catalog_seed_manifest(
        manifest,
        expected_recipe_count=1,
        min_per_cuisine_meal_type=0,
        expected_cuisine_counts=None,
    )

    assert result.is_valid is False
    assert any("protein_g must match ingredient sum" in error for error in result.errors)
    assert any("calories must match ingredient-derived" in error for error in result.errors)
