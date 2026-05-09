import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.infra.adapters.vision_ai_service import VisionAIService
from src.domain.strategies.meal_analysis_strategy import MealAnalysisStrategy


@pytest.fixture
def mock_ai_manager():
    manager = Mock()
    manager.generate_with_vision = AsyncMock(
        return_value={"dish_name": "test meal", "calories": 500}
    )
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
    with patch(
        "src.infra.adapters.vision_ai_service.AIModelManager"
    ) as mock_cls:
        mock_cls.get_instance.return_value = mock_ai_manager
        return VisionAIService()


def test_analyze_uses_ai_manager(service, mock_ai_manager):
    result = service.analyze(b"fake_image_bytes")

    mock_ai_manager.generate_with_vision.assert_called_once()
    assert "structured_data" in result


def test_analyze_with_strategy(service, mock_ai_manager, mock_strategy):
    result = service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert result["strategy_used"] == "BasicAnalysis"


def test_analyze_with_strategy_returns_structured_data(service, mock_ai_manager, mock_strategy):
    result = service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert result["structured_data"] == {"dish_name": "test meal", "calories": 500}
    assert "raw_response" in result


def test_analyze_with_strategy_calls_correct_purpose(service, mock_ai_manager, mock_strategy):
    from src.infra.services.ai.ai_model_manager import ModelPurpose

    service.analyze_with_strategy(b"fake_image", mock_strategy)

    call_kwargs = mock_ai_manager.generate_with_vision.call_args
    assert call_kwargs.kwargs["purpose"] == ModelPurpose.MEAL_SCAN


def test_analyze_with_strategy_passes_prompt_from_strategy(service, mock_ai_manager, mock_strategy):
    service.analyze_with_strategy(b"fake_image", mock_strategy)

    call_kwargs = mock_ai_manager.generate_with_vision.call_args
    assert call_kwargs.kwargs["prompt"] == "What food is this?"
    assert call_kwargs.kwargs["system_message"] == "Analyze this food"


def test_analyze_with_strategy_raises_runtime_error_on_failure(service, mock_ai_manager, mock_strategy):
    mock_ai_manager.generate_with_vision = AsyncMock(side_effect=Exception("AI failure"))

    with pytest.raises(RuntimeError, match="Failed to analyze image"):
        service.analyze_with_strategy(b"fake_image", mock_strategy)


def test_compress_image_still_works(service):
    from io import BytesIO
    from PIL import Image

    img = Image.new("RGB", (400, 300), color=(128, 64, 32))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=50)
    small_bytes = buf.getvalue()

    result = service._compress_image(small_bytes)

    assert result is small_bytes  # small JPEG skips compression
