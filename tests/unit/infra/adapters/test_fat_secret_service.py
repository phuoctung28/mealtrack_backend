from unittest.mock import AsyncMock

import pytest

from src.infra.adapters.fat_secret_service import FatSecretService


@pytest.mark.unit
def test_fatsecret_serving_units_preserve_fatsecret_order():
    service = FatSecretService("client", "secret")
    food = {
        "servings": {
            "serving": [
                {
                    "measurement_description": "serving",
                    "metric_serving_amount": "30.000",
                    "serving_description": "1 cup",
                },
                {
                    "measurement_description": "g",
                    "metric_serving_amount": "100.000",
                    "serving_description": "100 g",
                },
            ]
        }
    }

    units = service._extract_serving_units(food)

    assert units[0] == {
        "unit": "serving",
        "gram_weight": 30.0,
        "description": "1 cup",
    }
    assert units[1] == {"unit": "g", "gram_weight": 100.0, "description": "100 g"}


@pytest.mark.unit
def test_fatsecret_nutrition_prefers_100g_serving():
    service = FatSecretService("client", "secret")
    food = {
        "servings": {
            "serving": [
                {
                    "measurement_description": "serving",
                    "metric_serving_amount": "30.000",
                    "serving_description": "1 cup",
                    "calories": "100",
                    "protein": "3",
                    "carbohydrate": "20",
                    "fat": "2",
                },
                {
                    "measurement_description": "g",
                    "metric_serving_amount": "100.000",
                    "serving_description": "100 g",
                    "calories": "333",
                    "protein": "10",
                    "carbohydrate": "66.67",
                    "fat": "6.67",
                },
            ]
        }
    }

    nutrition = service._extract_nutrition_from_details(food)

    assert nutrition["calories_100g"] == 333.0
    assert nutrition["protein_100g"] == 10.0
    assert nutrition["carbs_100g"] == 66.67
    assert nutrition["fat_100g"] == 6.67
    assert nutrition["allowed_units"][0]["description"] == "1 cup"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fatsecret_search_uses_v5_methods():
    service = FatSecretService("client", "secret")
    service._api_request = AsyncMock(
        side_effect=[
            {
                "foods_search": {
                    "results": {
                        "food": [
                            {
                                "food_id": "50953",
                                "food_name": "Whole Grain Cheerios",
                                "brand_name": "General Mills",
                            }
                        ]
                    }
                }
            },
            {
                "food": {
                    "food_id": "50953",
                    "food_name": "Whole Grain Cheerios",
                    "servings": {
                        "serving": {
                            "measurement_description": "g",
                            "metric_serving_amount": "100.000",
                            "serving_description": "100 g",
                            "calories": "333",
                            "protein": "10",
                            "carbohydrate": "66.67",
                            "fat": "6.67",
                        }
                    },
                }
            },
        ]
    )

    results = await service.search_foods("cheerios", max_results=1)

    search_call = service._api_request.call_args_list[0]
    detail_call = service._api_request.call_args_list[1]
    search_params = search_call.kwargs["params"]
    detail_params = detail_call.kwargs["params"]
    assert search_call.args[0] == "POST"
    assert detail_call.args[0] == "POST"
    assert search_params["method"] == "foods.search.v5"
    assert search_params["flag_default_serving"] == "true"
    assert detail_params["method"] == "food.get.v5"
    assert results[0]["allowed_units"][0]["gram_weight"] == 100.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fatsecret_barcode_lookup_uses_method_based_endpoint():
    service = FatSecretService("client", "secret")
    service._api_request = AsyncMock(
        side_effect=[
            {"food_id": "50953"},
            {
                "food": {
                    "food_id": "50953",
                    "food_name": "Whole Grain Cheerios",
                    "servings": {
                        "serving": {
                            "measurement_description": "g",
                            "metric_serving_amount": "100.000",
                            "serving_description": "100 g",
                            "calories": "333",
                            "protein": "10",
                            "carbohydrate": "66.67",
                            "fat": "6.67",
                        }
                    },
                }
            },
        ]
    )

    result = await service.get_product("12345678")

    barcode_call = service._api_request.call_args_list[0]
    detail_call = service._api_request.call_args_list[1]
    detail_params = detail_call.kwargs["params"]
    assert barcode_call.args[0] == "POST"
    assert barcode_call.kwargs["params"]["method"] == "food.find_id_for_barcode"
    assert detail_call.args[0] == "POST"
    assert detail_params["method"] == "food.get.v5"
    assert result["allowed_units"][0] == {
        "unit": "g",
        "gram_weight": 100.0,
        "description": "100 g",
    }
