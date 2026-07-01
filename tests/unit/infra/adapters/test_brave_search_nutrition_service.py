from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.infra.adapters.brave_search_nutrition_service import (
    BraveSearchNutritionService,
)


def _service(ai_response):
    meal_generation = Mock()
    meal_generation.generate_meal_plan_async = AsyncMock(return_value=ai_response)
    return BraveSearchNutritionService(
        api_key="fake-key",
        meal_generation_service=meal_generation,
        macro_validation_service=Mock(),
    )


@pytest.mark.asyncio
async def test_extract_nutrition_treats_uncertain_prose_as_miss_without_json_parse():
    prose = (
        "I could not identify a specific food product from these search results. "
        "The snippets mention the barcode but do not provide a clear product name "
        "or nutrition facts, so there is not enough information to extract macros."
    )
    service = _service({"raw_content": prose})

    with patch(
        "src.infra.adapters.brave_search_nutrition_service.extract_json"
    ) as mock_extract:
        result = await service._extract_nutrition(
            "9999999999999",
            "Unclear result: barcode lookup page without product details",
            "en",
        )

    assert result is None
    mock_extract.assert_not_called()


@pytest.mark.asyncio
async def test_extract_nutrition_parses_valid_json_raw_content():
    service = _service(
        {
            "raw_content": (
                '{"name": "Test Cereal", "brand": "Test Brand", '
                '"protein_100g": 8.0, "carbs_100g": 72.0, "fat_100g": 2.5, '
                '"fiber_100g": 6.0, "sugar_100g": 18.0, '
                '"serving_size": "30g", "confidence": "high"}'
            )
        }
    )

    result = await service._extract_nutrition(
        "1234567890123",
        "Test Cereal: nutrition facts per 100g",
        "en",
    )

    assert result is not None
    assert result["name"] == "Test Cereal"
    assert result["protein_100g"] == 8.0


@pytest.mark.asyncio
async def test_extract_nutrition_uses_barcode_validator_without_fat_floor():
    service = _service(
        {
            "raw_content": (
                '{"name": "Test Soda", "protein_100g": 0, '
                '"carbs_100g": 11, "fat_100g": 0, "confidence": "high"}'
            )
        }
    )

    result = await service._extract_nutrition(
        "036000291452",
        "Test Soda nutrition",
        "en",
    )

    assert result is not None
    assert result["fat_100g"] == 0.0
    assert result["calories_100g"] == 44.0
