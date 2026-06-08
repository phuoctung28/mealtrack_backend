import base64
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from src.api.schemas.request.ingredient_recognition_requests import (
    MAX_IMAGE_BASE64_LENGTH,
    IngredientRecognitionRequest,
)
from src.app.commands.ingredient import RecognizeIngredientCommand
from src.app.handlers.command_handlers.recognize_ingredient_command_handler import (
    RecognizeIngredientCommandHandler,
)
from src.domain.exceptions.ai_exceptions import AIUnavailableError


@pytest.mark.asyncio
async def test_recognize_ingredient_rejects_invalid_base64_before_ai_call():
    vision_service = Mock()
    vision_service.analyze_with_strategy = AsyncMock()
    handler = RecognizeIngredientCommandHandler(vision_service=vision_service)

    result = await handler.handle(
        RecognizeIngredientCommand(image_data="not base64!!", language="en")
    )

    assert result["success"] is False
    assert result["message"] == "Invalid image data format"
    vision_service.analyze_with_strategy.assert_not_awaited()


@pytest.mark.asyncio
async def test_recognize_ingredient_rejects_decoded_image_over_5mb():
    vision_service = Mock()
    vision_service.analyze_with_strategy = AsyncMock()
    handler = RecognizeIngredientCommandHandler(vision_service=vision_service)
    oversized = base64.b64encode(b"x" * (5 * 1024 * 1024 + 1)).decode("ascii")

    result = await handler.handle(
        RecognizeIngredientCommand(image_data=oversized, language="en")
    )

    assert result["success"] is False
    assert result["message"] == "Image too large (max 5MB)"
    vision_service.analyze_with_strategy.assert_not_awaited()


@pytest.mark.asyncio
async def test_recognize_ingredient_preserves_ai_unavailable():
    unavailable = AIUnavailableError(
        "All vision models failed",
        attempted_models=["gemini-2.5-flash-lite", "gemini-2.5-flash"],
        last_error="503 UNAVAILABLE",
    )
    vision_service = Mock()
    vision_service.analyze_with_strategy = AsyncMock(side_effect=unavailable)
    handler = RecognizeIngredientCommandHandler(vision_service=vision_service)
    valid_image = base64.b64encode(b"image").decode("ascii")

    with pytest.raises(AIUnavailableError):
        await handler.handle(RecognizeIngredientCommand(image_data=valid_image))


def test_ingredient_request_rejects_oversized_base64_payload():
    with pytest.raises(ValidationError):
        IngredientRecognitionRequest(image_data="a" * (MAX_IMAGE_BASE64_LENGTH + 1))
