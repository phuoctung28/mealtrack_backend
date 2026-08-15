from src.api.routes.v1.meals_route_helpers import parsed_food_item_to_response
from src.app.schemas.meal_schemas import ParsedFoodItemDto
from src.domain.services.food_mapping_service import FoodMappingService
from src.domain.services.nutrition_integrity_policy import NutritionIntegrityError


def _provider_item() -> dict:
    return {
        "source": "fatsecret",
        "food_id": "fs-42",
        "description": "Rice",
        "protein_100g": 2.7,
        "carbs_100g": 28.0,
        "fat_100g": 0.3,
        "fiber_100g": 0.4,
        "sugar_100g": 0.1,
        "calories_100g": 126.1,
        "allowed_units": [{"unit": "g", "gram_weight": 100, "description": "100 g"}],
    }


def test_local_search_result_emits_one_canonical_origin_and_alias():
    result = FoodMappingService().map_search_item(
        {
            "source": "food_reference",
            "food_reference_id": 42,
            "is_verified": True,
            "description": "Rice",
            "protein_100g": 2.7,
            "carbs_100g": 28.0,
            "fat_100g": 0.3,
            "fiber_100g": 0.4,
            "sugar_100g": 0.1,
            "allowed_units": [{"unit": "g", "gram_weight": 1}],
        }
    )

    assert result["origin"] == "local"
    assert result["food_id"] == "food_reference:42"
    assert result["source_namespace"] == "food_reference"
    assert result["source_food_id"] == "42"
    assert result["nutrition_basis"] == "100g"
    assert result["nutrition_contract_version"] == "nutrition_integrity_v1"
    assert result["calories_per_100g"] == 124.7


def test_mismatching_local_alias_is_rejected():
    item = {
        "source": "food_reference",
        "food_reference_id": 42,
        "is_verified": True,
        "food_id": "food_reference:99",
        "description": "Rice",
        "protein_100g": 2.7,
        "carbs_100g": 28.0,
        "fat_100g": 0.3,
        "fiber_100g": 0.4,
        "sugar_100g": 0.1,
        "allowed_units": [{"unit": "g", "gram_weight": 1}],
    }

    try:
        FoodMappingService().map_search_item(item)
    except NutritionIntegrityError as exc:
        assert exc.result.reason_code == "origin_alias_mismatch"
    else:
        raise AssertionError("mismatching local alias must be rejected")


def test_provider_search_result_uses_namespaced_opaque_identity():
    result = FoodMappingService().map_search_item(_provider_item())

    assert result["origin"] == "provider"
    assert result["source_namespace"] == "fatsecret"
    assert result["source_food_id"] == "fs-42"
    assert result["food_id"] == "fatsecret:fs-42"
    assert result["allowed_units"] == [
        {"unit": "g", "gram_weight": 1.0, "description": "1 g"},
        {"unit": "serving", "gram_weight": 100.0, "description": "100 g"},
    ]


def test_usda_search_result_uses_namespaced_fdc_identity():
    result = FoodMappingService().map_search_item(
        {
            "fdcId": 170000,
            "description": "Rice",
            "foodNutrients": [
                {"nutrientId": 1003, "value": 2.7},
                {"nutrientId": 1005, "value": 28.0},
                {"nutrientId": 1004, "value": 0.3},
                {"nutrientId": 1079, "value": 0.4},
                {"nutrientId": 2000, "value": 0.1},
                {"nutrientId": 1008, "value": 126.1},
            ],
        }
    )

    assert result["origin"] == "usda"
    assert result["source_namespace"] == "usda_fdc"
    assert result["source_food_id"] == "170000"
    assert result["food_id"] == "usda_fdc:170000"


def test_parse_response_keeps_legacy_fields_and_adds_identity_metadata():
    response = parsed_food_item_to_response(
        ParsedFoodItemDto(
            name="Rice",
            quantity=100,
            unit="g",
            protein=2.7,
            carbs=28.0,
            fat=0.3,
            fiber=0.4,
            origin="provider",
            food_id="fatsecret:fs-42",
            source_namespace="fatsecret",
            source_food_id="fs-42",
            nutrition_basis="100g",
            nutrition_contract_version="nutrition_integrity_v1",
            calories_per_100g=124.7,
        )
    )

    assert response.calories == 124.7
    assert response.origin == "provider"
    assert response.food_id == "fatsecret:fs-42"
    assert response.source_namespace == "fatsecret"
    assert response.source_food_id == "fs-42"
    assert response.calories_per_100g == 124.7
