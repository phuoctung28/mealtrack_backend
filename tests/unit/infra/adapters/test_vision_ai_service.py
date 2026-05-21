from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from src.infra.adapters.vision_ai_service import VisionAIService

_MGR_PATCH = "src.infra.adapters.vision_ai_service.AIModelManager"


def _make_jpeg(width: int, height: int, quality: int = 95) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _make_service() -> VisionAIService:
    with patch(_MGR_PATCH) as mock_cls:
        mock_manager = MagicMock()
        mock_manager.generate_with_vision = AsyncMock(
            return_value={"dish_name": "test", "ingredients": []}
        )
        mock_cls.get_instance.return_value = mock_manager
        return VisionAIService()


def test_vision_service_uses_ai_model_manager():
    with patch(_MGR_PATCH) as mock_cls:
        mock_manager = MagicMock()
        mock_manager.generate_with_vision = AsyncMock(return_value={})
        mock_cls.get_instance.return_value = mock_manager

        VisionAIService()

        mock_cls.get_instance.assert_called_once()


def test_compress_image_resizes_large_image():
    service = _make_service()
    large_bytes = _make_jpeg(2000, 1500)

    result = service._compress_image(large_bytes)

    img = Image.open(BytesIO(result))
    assert max(img.size) <= 768


def test_compress_image_skips_small_image():
    service = _make_service()
    # Fast-path only applies to small JPEGs — PNG/WebP always get converted
    small_bytes = _make_jpeg(400, 300, quality=50)
    assert len(small_bytes) < 200 * 1024  # confirm precondition

    result = service._compress_image(small_bytes)

    assert result is small_bytes  # skip path returns original object unchanged


def test_compress_image_fallback_on_corrupt_bytes():
    service = _make_service()
    corrupt = b"not an image at all"

    result = service._compress_image(corrupt)

    assert result == corrupt


def test_analyze_with_strategy_compresses_before_sending():
    service = _make_service()

    large_bytes = _make_jpeg(2000, 1500)

    from src.domain.strategies.meal_analysis_strategy import AnalysisStrategyFactory

    strategy = AnalysisStrategyFactory.create_basic_strategy()

    service.analyze_with_strategy(large_bytes, strategy)

    # Verify generate_with_vision was called with compressed image data
    call_kwargs = service._ai_manager.generate_with_vision.call_args
    image_data = call_kwargs.kwargs["image_data"]

    # The image should be compressed (smaller than 2000x1500)
    img = Image.open(BytesIO(image_data))
    assert max(img.size) <= 768


def test_analyze_with_strategy_passes_max_tokens_1024():
    """Vision calls must pass max_tokens=1024, not use the 4096 default."""
    service = _make_service()
    from src.domain.strategies.meal_analysis_strategy import AnalysisStrategyFactory
    strategy = AnalysisStrategyFactory.create_basic_strategy()

    image = _make_jpeg(400, 300)
    service.analyze_with_strategy(image, strategy)

    call_kwargs = service._ai_manager.generate_with_vision.call_args.kwargs
    assert call_kwargs.get("max_tokens") == 1024


def test_analyze_by_url_passes_max_tokens_1024():
    """analyze_by_url_with_strategy must also pass max_tokens=1024."""
    service = _make_service()
    from src.domain.strategies.meal_analysis_strategy import AnalysisStrategyFactory
    strategy = AnalysisStrategyFactory.create_basic_strategy()

    service.analyze_by_url_with_strategy("http://example.com/food.jpg", strategy)

    call_kwargs = service._ai_manager.generate_with_vision.call_args.kwargs
    assert call_kwargs.get("max_tokens") == 1024


def test_recipe_token_limit_is_1200():
    """PARALLEL_SINGLE_MEAL_TOKENS must be 1200, not 4000."""
    from src.domain.services.meal_suggestion.recipe_attempt_builder import (
        PARALLEL_SINGLE_MEAL_TOKENS,
    )
    assert PARALLEL_SINGLE_MEAL_TOKENS == 1200
