from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.exceptions.ai_exceptions import (
    AIOutputValidationError,
    AIUnavailableError,
)
from src.domain.model.ai.nutrition_contracts import (
    FoodLabelNutritionResponse,
    VisionNutritionResponse,
)
from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.parsers.vision_response_parser import VisionResponseParser
from src.domain.strategies.meal_analysis_strategy import (
    AnalysisStrategyFactory,
    FoodLabelImageAnalysisStrategy,
    MealAnalysisStrategy,
)
from src.infra.adapters.vision_ai_service import VisionAIService


def _valid_vision_response():
    return {
        "dish_name": "test meal",
        "foods": [
            {
                "name": "rice",
                "quantity_g": 180,
                "macros": {"protein_g": 4, "carbs_g": 50, "fat_g": 1},
            }
        ],
        "confidence": 0.8,
    }


@pytest.fixture
def mock_ai_manager():
    manager = Mock()
    manager.generate_with_vision = AsyncMock(return_value=_valid_vision_response())
    return manager


@pytest.fixture
def mock_strategy():
    strategy = Mock(spec=MealAnalysisStrategy)
    strategy.get_analysis_prompt.return_value = "Analyze this food"
    strategy.get_user_message.return_value = "What food is this?"
    strategy.get_strategy_name.return_value = "BasicAnalysis"
    return strategy


@pytest.fixture
def service(mock_ai_manager):
    with patch("src.infra.adapters.vision_ai_service.AIModelManager") as mock_cls:
        mock_cls.get_instance.return_value = mock_ai_manager
        return VisionAIService()


@pytest.mark.asyncio
async def test_analyze_uses_ai_manager(service, mock_ai_manager):
    result = await service.analyze(b"fake_image_bytes")

    mock_ai_manager.generate_with_vision.assert_called_once()
    assert "structured_data" in result


@pytest.mark.asyncio
async def test_analyze_with_strategy(service, mock_ai_manager, mock_strategy):
    result = await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert result["strategy_used"] == "BasicAnalysis"


@pytest.mark.asyncio
async def test_analyze_with_strategy_returns_structured_data(
    service, mock_ai_manager, mock_strategy
):
    result = await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert result["structured_data"]["dish_name"] == "test meal"
    assert result["structured_data"]["foods"][0]["quantity_g"] == 180
    assert "unit" not in result["structured_data"]["foods"][0]
    assert "raw_response" in result
    assert (
        VisionResponseParser().parse_to_nutrition(result).food_items[0].quantity == 180
    )
    assert (
        GPTResponseParser().parse_to_nutrition(result).food_items[0].macros.protein == 4
    )


@pytest.mark.asyncio
async def test_analyze_with_strategy_preserves_non_food_guard(
    service, mock_ai_manager, mock_strategy
):
    mock_ai_manager.generate_with_vision = AsyncMock(
        return_value={
            "is_food": False,
            "dish_name": None,
            "foods": [],
            "confidence": 0.95,
        }
    )

    result = await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert result["structured_data"]["is_food"] is False
    assert result["structured_data"]["foods"] == []

    assert GPTResponseParser().parse_is_food(result) is False


@pytest.mark.asyncio
async def test_analyze_with_strategy_calls_correct_purpose(
    service, mock_ai_manager, mock_strategy
):
    from src.infra.services.ai.ai_model_manager import ModelPurpose

    await service.analyze_with_strategy(b"fake_image", mock_strategy)

    call_kwargs = mock_ai_manager.generate_with_vision.call_args
    assert call_kwargs.kwargs["purpose"] == ModelPurpose.MEAL_SCAN
    assert call_kwargs.kwargs["schema"] is VisionNutritionResponse


@pytest.mark.asyncio
async def test_analyze_with_strategy_uses_food_label_schema_for_label_images(
    service, mock_ai_manager
):
    mock_ai_manager.generate_with_vision = AsyncMock(
        return_value={
            "is_food_label": True,
            "product_name": "Protein Bar",
            "brand": None,
            "serving_size": {"display_text": "55g", "grams": 55},
            "servings_per_package": 8,
            "label_calories_per_serving": 210,
            "macros_per_serving": {
                "protein_g": 12,
                "carbs_g": 24,
                "fat_g": 7,
                "fiber_g": 5,
                "sugar_g": 8,
            },
            "confidence": 0.9,
            "label_notes": ["Read from label image."],
        }
    )
    strategy = FoodLabelImageAnalysisStrategy()

    result = await service.analyze_with_strategy(b"fake_image", strategy)

    call_kwargs = mock_ai_manager.generate_with_vision.call_args.kwargs
    from src.infra.services.ai.ai_model_manager import ModelPurpose

    assert call_kwargs["purpose"] == ModelPurpose.FOOD_LABEL_SCAN
    assert call_kwargs["schema"] is FoodLabelNutritionResponse
    assert call_kwargs["system_message"] == strategy.get_analysis_prompt()
    assert result["structured_data"]["product_name"] == "Protein Bar"


@pytest.mark.asyncio
async def test_analyze_with_strategy_passes_prompt_from_strategy(
    service, mock_ai_manager, mock_strategy
):
    await service.analyze_with_strategy(b"fake_image", mock_strategy)

    call_kwargs = mock_ai_manager.generate_with_vision.call_args
    assert call_kwargs.kwargs["prompt"] == "What food is this?"
    assert call_kwargs.kwargs["system_message"] == "Analyze this food"


@pytest.mark.asyncio
async def test_analyze_with_strategy_raises_runtime_error_on_failure(
    service, mock_ai_manager, mock_strategy
):
    mock_ai_manager.generate_with_vision = AsyncMock(
        side_effect=Exception("AI failure")
    )

    with pytest.raises(RuntimeError, match="Failed to analyze image"):
        await service.analyze_with_strategy(b"fake_image", mock_strategy)


@pytest.mark.asyncio
async def test_analyze_with_strategy_preserves_ai_unavailable(
    service, mock_ai_manager, mock_strategy
):
    unavailable = AIUnavailableError(
        "All vision models failed",
        attempted_models=["gpt-5.4-mini-2026-03-17", "gpt-5.4-mini-2026-03-17"],
        last_error="503 UNAVAILABLE",
    )
    mock_ai_manager.generate_with_vision = AsyncMock(side_effect=unavailable)

    with pytest.raises(AIUnavailableError) as exc_info:
        await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert exc_info.value.attempted_models == [
        "gpt-5.4-mini-2026-03-17",
        "gpt-5.4-mini-2026-03-17",
    ]
    assert mock_ai_manager.generate_with_vision.await_count == 1


@pytest.mark.asyncio
async def test_analyze_with_strategy_does_not_retry_invalid_structured_output(
    service, mock_ai_manager, mock_strategy
):
    mock_ai_manager.generate_with_vision = AsyncMock(
        return_value={
            "dish_name": "Rice bowl",
            "foods": [
                {
                    "name": "rice",
                    "quantity_g": 150000,
                    "macros": {"protein_g": 4, "carbs_g": 50, "fat_g": 1},
                }
            ],
        }
    )

    with pytest.raises(AIOutputValidationError) as exc_info:
        await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert mock_ai_manager.generate_with_vision.await_count == 1
    call_kwargs = mock_ai_manager.generate_with_vision.await_args.kwargs
    assert call_kwargs["purpose"].value == "meal_scan"
    assert exc_info.value.purpose == "meal_scan"
    assert exc_info.value.attempt_count == 1
    assert "foods.0.quantity_g" in exc_info.value.validation_details[0]


@pytest.mark.asyncio
async def test_analyze_with_strategy_raises_controlled_error_without_repair_retry(
    service, mock_ai_manager, mock_strategy
):
    invalid = {
        "dish_name": "Rice bowl",
        "foods": [
            {
                "name": "rice",
                "quantity_g": 150000,
                "macros": {"protein_g": 4, "carbs_g": 50, "fat_g": 1},
            }
        ],
    }
    mock_ai_manager.generate_with_vision = AsyncMock(return_value=invalid)

    with pytest.raises(AIOutputValidationError) as exc_info:
        await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert mock_ai_manager.generate_with_vision.await_count == 1
    assert exc_info.value.purpose == "meal_scan"
    assert exc_info.value.attempt_count == 1
    assert "foods.0.quantity_g" in exc_info.value.validation_details[0]


@pytest.mark.asyncio
async def test_ingredient_identification_keeps_unstructured_contract(
    service, mock_ai_manager
):
    mock_ai_manager.generate_with_vision = AsyncMock(
        return_value={
            "name": "broccoli",
            "confidence": 0.94,
            "category": "vegetable",
        }
    )
    strategy = AnalysisStrategyFactory.create_ingredient_identification_strategy()

    result = await service.analyze_with_strategy(b"fake_image", strategy)

    call_kwargs = mock_ai_manager.generate_with_vision.await_args.kwargs
    assert "schema" not in call_kwargs
    assert mock_ai_manager.generate_with_vision.await_count == 1
    assert result["strategy_used"] == "IngredientIdentification"
    assert result["structured_data"] == {
        "name": "broccoli",
        "confidence": 0.94,
        "category": "vegetable",
    }


def test_compress_image_still_works(service):
    from io import BytesIO

    from PIL import Image

    img = Image.new("RGB", (400, 300), color=(128, 64, 32))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=50)
    small_bytes = buf.getvalue()

    result = service._compress_image(small_bytes)

    assert result is small_bytes  # small JPEG skips compression
