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
