"""Tests that upload_meal_image_immediately_command_handler emits phase spans."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler import (
    UploadMealImageImmediatelyHandler,
)
from src.app.commands.meal import UploadMealImageImmediatelyCommand


def _make_handler():
    handler = UploadMealImageImmediatelyHandler(
        image_store=MagicMock(),
        vision_service=MagicMock(),
        gpt_parser=MagicMock(),
        cache_service=AsyncMock(),
    )
    return handler


def _mock_span():
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=False)
    return span


@pytest.mark.asyncio
async def test_handle_emits_phase1_vision_span():
    """handle() emits a PHASE-1 Vision Analysis span."""
    handler = _make_handler()
    handler.image_store.save.return_value = "mock://images/550e8400-e29b-41d4-a716-446655440000"
    handler.vision_service.analyze.return_value = {"raw_response": '{"dish_name": "pizza"}', "structured_data": {}}
    handler.gpt_parser.parse_to_nutrition.return_value = MagicMock(food_items=[MagicMock()], calories=500)
    handler.gpt_parser.parse_dish_name.return_value = "pizza"
    handler.gpt_parser.parse_emoji.return_value = "🍕"
    handler.gpt_parser.extract_raw_json.return_value = "{}"

    mock_span = _mock_span()
    span_calls = []

    def track_span(op=None, name=None, **kwargs):
        span_calls.append((op, name))
        return mock_span

    with patch("sentry_sdk.start_span", side_effect=track_span):
        with patch("src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler.UnitOfWork") as mock_uow:
            mock_uow_ctx = MagicMock()
            mock_uow_ctx.__enter__ = MagicMock(return_value=mock_uow_ctx)
            mock_uow_ctx.__exit__ = MagicMock(return_value=False)
            mock_uow_ctx.users.get_user_timezone.return_value = "UTC"
            saved = MagicMock()
            saved.meal_id = "meal-1"
            mock_uow_ctx.meals.save.return_value = saved
            mock_uow_ctx.meals.find_by_id.return_value = saved
            mock_uow.return_value = mock_uow_ctx

            cmd = UploadMealImageImmediatelyCommand(
                user_id="550e8400-e29b-41d4-a716-446655440001",
                file_contents=b"fake",
                content_type="image/jpeg",
                language="en",
            )
            await handler.handle(cmd)

    assert ("gen_ai.invoke_agent", "PHASE-1: Vision Analysis") in span_calls


@pytest.mark.asyncio
async def test_handle_emits_phase2_translation_span_for_non_english():
    """handle() emits a PHASE-2 Translation span when language is non-English."""
    handler = _make_handler()
    handler.meal_translation_service = AsyncMock()
    handler.meal_translation_service.translate_meal = AsyncMock(return_value=MagicMock())
    handler.image_store.save.return_value = "mock://images/550e8400-e29b-41d4-a716-446655440000"
    handler.vision_service.analyze.return_value = {"raw_response": '{"dish_name": "pizza"}', "structured_data": {}}
    handler.gpt_parser.parse_to_nutrition.return_value = MagicMock(food_items=[MagicMock()], calories=500)
    handler.gpt_parser.parse_dish_name.return_value = "pizza"
    handler.gpt_parser.parse_emoji.return_value = "🍕"
    handler.gpt_parser.extract_raw_json.return_value = "{}"

    mock_span = _mock_span()
    span_calls = []

    def track_span(op=None, name=None, **kwargs):
        span_calls.append((op, name))
        return mock_span

    with patch("sentry_sdk.start_span", side_effect=track_span):
        with patch("src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler.UnitOfWork") as mock_uow:
            mock_uow_ctx = MagicMock()
            mock_uow_ctx.__enter__ = MagicMock(return_value=mock_uow_ctx)
            mock_uow_ctx.__exit__ = MagicMock(return_value=False)
            mock_uow_ctx.users.get_user_timezone.return_value = "UTC"
            saved = MagicMock()
            saved.meal_id = "meal-1"
            mock_uow_ctx.meals.save.return_value = saved
            mock_uow_ctx.meals.find_by_id.return_value = saved
            mock_uow.return_value = mock_uow_ctx

            cmd = UploadMealImageImmediatelyCommand(
                user_id="550e8400-e29b-41d4-a716-446655440001",
                file_contents=b"fake",
                content_type="image/jpeg",
                language="vi",
            )
            await handler.handle(cmd)

    assert ("gen_ai.invoke_agent", "PHASE-2: Translation") in span_calls
