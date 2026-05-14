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


def test_zero_float_quantity_is_silently_dropped():
    """GPT sometimes returns quantity=0.0 for trace ingredients — must not raise."""
    payload = {
        "foods": [
            {"name": "Rice", "quantity": 1.0, "unit": "cup", "macros": {"protein": 3, "carbs": 45, "fat": 0}},
            {"name": "Sauce", "quantity": 0.0, "unit": "tbsp", "macros": {"protein": 0, "carbs": 0, "fat": 0}},
        ]
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert len(result.foods) == 1
    assert result.foods[0].name == "Rice"


def test_zero_integer_quantity_is_silently_dropped():
    payload = {
        "foods": [
            {"name": "Rice", "quantity": 200, "unit": "g", "macros": {"protein": 4, "carbs": 40, "fat": 1}},
            {"name": "Ghost", "quantity": 0, "unit": "g", "macros": {"protein": 0, "carbs": 0, "fat": 0}},
        ]
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert len(result.foods) == 1
    assert result.foods[0].name == "Rice"


def test_negative_quantity_is_silently_dropped():
    payload = {
        "foods": [
            {"name": "Rice", "quantity": 200, "unit": "g", "macros": {"protein": 4, "carbs": 40, "fat": 1}},
            {"name": "Bad", "quantity": -1.0, "unit": "g", "macros": {"protein": 0, "carbs": 0, "fat": 0}},
        ]
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert len(result.foods) == 1


def test_non_numeric_quantity_is_silently_dropped():
    """String quantity that can't be parsed as positive float is dropped."""
    payload = {
        "foods": [
            {"name": "Rice", "quantity": 200, "unit": "g", "macros": {"protein": 4, "carbs": 40, "fat": 1}},
            {"name": "Bad", "quantity": "unknown", "unit": "g", "macros": {"protein": 0, "carbs": 0, "fat": 0}},
        ]
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert len(result.foods) == 1
    assert result.foods[0].name == "Rice"


def test_all_zero_quantity_foods_results_in_empty_list():
    payload = {
        "foods": [
            {"name": "A", "quantity": 0.0, "unit": "g", "macros": {"protein": 0, "carbs": 0, "fat": 0}},
            {"name": "B", "quantity": 0, "unit": "g", "macros": {"protein": 0, "carbs": 0, "fat": 0}},
        ]
    }

    result = VisionAnalyzeResponse.model_validate(payload)

    assert result.foods == []
