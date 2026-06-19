from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.exceptions.ai_exceptions import (
    AIOutputValidationError,
    AIUnavailableError,
)
from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
from src.domain.strategies.meal_analysis_strategy import (
    AnalysisStrategyFactory,
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
                "macros": {"protein": 4, "carbs": 50, "fat": 1},
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
    assert result["structured_data"]["foods"][0]["quantity"] == 180
    assert result["structured_data"]["foods"][0]["unit"] == "g"
    assert "raw_response" in result


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

    from src.domain.parsers.gpt_response_parser import GPTResponseParser

    assert GPTResponseParser().parse_is_food(result) is False


@pytest.mark.asyncio
async def test_analyze_with_strategy_calls_correct_purpose(
    service, mock_ai_manager, mock_strategy
):
    from src.infra.services.ai.ai_model_manager import ModelPurpose

    await service.analyze_with_strategy(b"fake_image", mock_strategy)

    call_kwargs = mock_ai_manager.generate_with_vision.call_args
    assert call_kwargs.kwargs["purpose"] == ModelPurpose.MEAL_SCAN


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
    mock_ai_manager.generate_with_vision = AsyncMock(side_effect=Exception("AI failure"))

    with pytest.raises(RuntimeError, match="Failed to analyze image"):
        await service.analyze_with_strategy(b"fake_image", mock_strategy)


@pytest.mark.asyncio
async def test_analyze_with_strategy_preserves_ai_unavailable(
    service, mock_ai_manager, mock_strategy
):
    unavailable = AIUnavailableError(
        "All vision models failed",
        attempted_models=["gemini-2.5-flash-lite", "gemini-2.5-flash"],
        last_error="503 UNAVAILABLE",
    )
    mock_ai_manager.generate_with_vision = AsyncMock(side_effect=unavailable)

    with pytest.raises(AIUnavailableError) as exc_info:
        await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert exc_info.value.attempted_models == [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]
    assert mock_ai_manager.generate_with_vision.await_count == 1


@pytest.mark.asyncio
async def test_analyze_with_strategy_retries_invalid_structured_output_once(
    service, mock_ai_manager, mock_strategy
):
    mock_ai_manager.generate_with_vision = AsyncMock(
        side_effect=[
            {
                "dish_name": "Rice bowl",
                "foods": [
                    {
                        "name": "rice",
                        "quantity_g": 150000,
                        "macros": {"protein": 4, "carbs": 50, "fat": 1},
                    }
                ],
            },
            {
                "dish_name": "Rice bowl",
                "foods": [
                    {
                        "name": "rice",
                        "quantity_g": 180,
                        "macros": {"protein": 4, "carbs": 50, "fat": 1},
                    }
                ],
                "confidence": 0.8,
            },
        ]
    )

    result = await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert mock_ai_manager.generate_with_vision.await_count == 2
    second_call = mock_ai_manager.generate_with_vision.await_args_list[1].kwargs
    assert "Return the full corrected response" in second_call["prompt"]
    assert "foods.0.quantity_g" in second_call["prompt"]
    assert result["structured_data"]["foods"][0]["quantity"] == 180
    assert result["structured_data"]["foods"][0]["unit"] == "g"
    assert result["structured_data"]["foods"][0]["macros"] == {
        "protein": 4.0,
        "carbs": 50.0,
        "fat": 1.0,
    }


@pytest.mark.asyncio
async def test_analyze_with_strategy_raises_controlled_error_after_retry_failure(
    service, mock_ai_manager, mock_strategy
):
    invalid = {
        "dish_name": "Rice bowl",
        "foods": [
            {
                "name": "rice",
                "quantity_g": 150000,
                "macros": {"protein": 4, "carbs": 50, "fat": 1},
            }
        ],
    }
    mock_ai_manager.generate_with_vision = AsyncMock(side_effect=[invalid, invalid])

    with pytest.raises(AIOutputValidationError) as exc_info:
        await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert mock_ai_manager.generate_with_vision.await_count == 2
    assert exc_info.value.purpose == "meal_scan"
    assert exc_info.value.attempt_count == 2
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
