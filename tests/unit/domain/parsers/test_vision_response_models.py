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
