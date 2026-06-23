import pytest

from src.domain.exceptions.ai_exceptions import AIOutputValidationError
from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
from src.domain.services.ai_output_validation_service import (
    build_validation_retry_prompt,
    validate_ai_output,
)


def test_validate_ai_output_returns_contract_dump():
    payload = {
        "dish_name": "Rice bowl",
        "foods": [
            {
                "name": "rice",
                "quantity_g": 180,
                "macros": {"protein": 4, "carbs": 50, "fat": 1},
            }
        ],
    }

    result = validate_ai_output(
        payload,
        schema=VisionNutritionResponse,
        purpose="meal_scan",
        attempt_count=1,
    )

    assert result["foods"][0]["quantity_g"] == pytest.approx(180)
    assert "calories" not in result


def test_validate_ai_output_raises_sanitized_error_details():
    payload = {
        "foods": [
            {
                "name": "rice",
                "quantity_g": 150000,
                "macros": {"protein": 4, "carbs": 50, "fat": 1},
            }
        ],
    }

    with pytest.raises(AIOutputValidationError) as exc_info:
        validate_ai_output(
            payload,
            schema=VisionNutritionResponse,
            purpose="meal_scan",
            attempt_count=1,
        )

    assert exc_info.value.purpose == "meal_scan"
    assert exc_info.value.attempt_count == 1
    assert exc_info.value.validation_details
    assert "foods.0.quantity_g" in exc_info.value.validation_details[0]
    assert "150000" not in exc_info.value.validation_details[0]


def test_build_validation_retry_prompt_uses_compact_correction_context():
    error = AIOutputValidationError(
        "Invalid AI output",
        purpose="meal_scan",
        attempt_count=1,
        validation_details=["foods.0.quantity_g: Input should be <= 10000"],
    )

    prompt = build_validation_retry_prompt("Analyze this image.", error)

    assert prompt.startswith("Analyze this image.")
    assert "Return the full corrected response" in prompt
    assert "foods.0.quantity_g" in prompt
