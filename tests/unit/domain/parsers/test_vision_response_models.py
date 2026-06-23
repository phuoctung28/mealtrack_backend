"""Tests for vision response schema validation."""

import pytest
from pydantic import ValidationError

from src.domain.parsers.vision_response_models import VisionAnalyzeResponse


def test_valid_vision_response_payload():
    payload = {
        "dish_name": "Grilled Chicken Bowl",
        "foods": [
            {
                "name": "Grilled Chicken",
                "quantity": 150,
                "unit": "g",
                "macros": {"protein": 35, "carbs": 0, "fat": 5},
            }
        ],
        "confidence": 0.92,
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert result.dish_name == "Grilled Chicken Bowl"
    assert result.foods[0].macros.protein == 35
    assert result.confidence == pytest.approx(0.92)


def test_missing_macros_fails_validation():
    payload = {
        "dish_name": "Simple Salad",
        "foods": [
            {
                "name": "Lettuce",
                "quantity": 50,
                "unit": "g",
            }
        ],
        "confidence": 0.7,
    }

    with pytest.raises(ValidationError):
        VisionAnalyzeResponse.model_validate(payload)


def test_missing_dish_name_is_allowed():
    payload = {
        "foods": [
            {
                "name": "Lettuce",
                "quantity": 50,
                "unit": "g",
                "macros": {"protein": 1, "carbs": 2, "fat": 0},
            }
        ],
        "confidence": 0.7,
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert result.dish_name is None
    assert result.foods[0].name == "Lettuce"


def test_missing_foods_is_allowed():
    payload = {
        "dish_name": "Mystery Meal",
        "confidence": 0.8,
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert result.foods is None
    assert result.confidence == pytest.approx(0.8)


def test_empty_foods_is_allowed():
    payload = {
        "dish_name": "Mystery Meal",
        "foods": [],
        "confidence": 0.8,
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert result.foods == []
    assert result.confidence == pytest.approx(0.8)


def test_missing_confidence_defaults():
    payload = {
        "foods": [
            {
                "name": "Lettuce",
                "quantity": 50,
                "unit": "g",
                "macros": {"protein": 1, "carbs": 2, "fat": 0},
            }
        ]
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert result.confidence == pytest.approx(0.5)


def test_is_food_defaults_true():
    payload = {
        "foods": [
            {
                "name": "Lettuce",
                "quantity": 50,
                "unit": "g",
                "macros": {"protein": 1, "carbs": 2, "fat": 0},
            }
        ]
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert result.is_food is True


def test_is_food_allows_false_with_empty_foods():
    payload = {
        "is_food": False,
        "dish_name": None,
        "foods": [],
        "confidence": 0.2,
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert result.is_food is False
    assert result.foods == []


def test_out_of_range_confidence_is_allowed_for_parser_clamping():
    payload = {
        "foods": [
            {
                "name": "Lettuce",
                "quantity": 50,
                "unit": "g",
                "macros": {"protein": 1, "carbs": 2, "fat": 0},
            }
        ],
        "confidence": 1.2,
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert result.confidence == pytest.approx(1.2)


def test_zero_float_quantity_fails_validation():
    """Invalid AI output must fail validation instead of silently dropping foods."""
    payload = {
        "foods": [
            {
                "name": "Rice",
                "quantity": 1.0,
                "unit": "cup",
                "macros": {"protein": 3, "carbs": 45, "fat": 0},
            },
            {
                "name": "Sauce",
                "quantity": 0.0,
                "unit": "tbsp",
                "macros": {"protein": 0, "carbs": 0, "fat": 0},
            },
        ]
    }

    with pytest.raises(ValidationError):
        VisionAnalyzeResponse.model_validate(payload)


def test_zero_integer_quantity_fails_validation():
    payload = {
        "foods": [
            {
                "name": "Rice",
                "quantity": 200,
                "unit": "g",
                "macros": {"protein": 4, "carbs": 40, "fat": 1},
            },
            {
                "name": "Ghost",
                "quantity": 0,
                "unit": "g",
                "macros": {"protein": 0, "carbs": 0, "fat": 0},
            },
        ]
    }

    with pytest.raises(ValidationError):
        VisionAnalyzeResponse.model_validate(payload)


def test_negative_quantity_fails_validation():
    payload = {
        "foods": [
            {
                "name": "Rice",
                "quantity": 200,
                "unit": "g",
                "macros": {"protein": 4, "carbs": 40, "fat": 1},
            },
            {
                "name": "Bad",
                "quantity": -1.0,
                "unit": "g",
                "macros": {"protein": 0, "carbs": 0, "fat": 0},
            },
        ]
    }

    with pytest.raises(ValidationError):
        VisionAnalyzeResponse.model_validate(payload)


def test_non_numeric_quantity_fails_validation():
    """String quantity that can't be parsed as positive float must fail."""
    payload = {
        "foods": [
            {
                "name": "Rice",
                "quantity": 200,
                "unit": "g",
                "macros": {"protein": 4, "carbs": 40, "fat": 1},
            },
            {
                "name": "Bad",
                "quantity": "unknown",
                "unit": "g",
                "macros": {"protein": 0, "carbs": 0, "fat": 0},
            },
        ]
    }

    with pytest.raises(ValidationError):
        VisionAnalyzeResponse.model_validate(payload)


def test_over_max_quantity_fails_validation():
    payload = {
        "foods": [
            {
                "name": "Rice",
                "quantity": 200,
                "unit": "g",
                "macros": {"protein": 4, "carbs": 40, "fat": 1},
            },
            {
                "name": "Bad",
                "quantity": 150000,
                "unit": "g",
                "macros": {"protein": 0, "carbs": 0, "fat": 0},
            },
        ]
    }

    with pytest.raises(ValidationError):
        VisionAnalyzeResponse.model_validate(payload)


def test_all_zero_quantity_foods_fails_validation():
    payload = {
        "foods": [
            {
                "name": "A",
                "quantity": 0.0,
                "unit": "g",
                "macros": {"protein": 0, "carbs": 0, "fat": 0},
            },
            {
                "name": "B",
                "quantity": 0,
                "unit": "g",
                "macros": {"protein": 0, "carbs": 0, "fat": 0},
            },
        ]
    }

    with pytest.raises(ValidationError):
        VisionAnalyzeResponse.model_validate(payload)


def test_full_prompt_response_with_emoji_and_calories():
    """Complete response including all prompt-required fields."""
    payload = {
        "dish_name": "Pho Bo",
        "emoji": "🍜",
        "total_calories": 520,
        "foods": [
            {
                "name": "Rice noodles",
                "quantity": 200,
                "unit": "g",
                "calories": 210,
                "macros": {"protein": 4, "carbs": 48, "fat": 1},
            },
            {
                "name": "Beef slices",
                "quantity": 100,
                "unit": "g",
                "calories": 200,
                "macros": {"protein": 26, "carbs": 0, "fat": 10},
            },
        ],
        "confidence": 0.88,
    }
    result = VisionAnalyzeResponse.model_validate(payload)
    assert result.emoji == "🍜"
    assert result.total_calories == pytest.approx(520)
    assert result.foods[0].calories == pytest.approx(210)
    assert result.foods[1].calories == pytest.approx(200)


def test_legacy_payload_without_emoji_or_total_calories():
    """Existing responses without new optional fields must still validate."""
    payload = {
        "dish_name": "Rice",
        "foods": [{"name": "Rice", "quantity": 100, "unit": "g", "macros": {"protein": 3, "carbs": 28, "fat": 0}}],
        "confidence": 0.9,
    }
    result = VisionAnalyzeResponse.model_validate(payload)
    assert result.emoji is None
    assert result.total_calories is None
    assert result.foods[0].calories is None


def test_schema_is_json_serializable():
    """model_json_schema() must return a dict with all prompt-required fields."""
    schema = VisionAnalyzeResponse.model_json_schema()
    assert isinstance(schema, dict)
    assert "dish_name" in schema.get("properties", {})
    assert "emoji" in schema.get("properties", {})
    assert "total_calories" in schema.get("properties", {})
    assert "confidence" in schema.get("properties", {})


def test_food_item_calories_is_optional():
    """calories field on FoodItemResponse is optional."""
    payload = {
        "name": "Apple",
        "quantity": 150,
        "unit": "g",
        "macros": {"protein": 0, "carbs": 20, "fat": 0},
    }
    from src.domain.parsers.vision_response_models import FoodItemResponse
    item = FoodItemResponse.model_validate(payload)
    assert item.calories is None
