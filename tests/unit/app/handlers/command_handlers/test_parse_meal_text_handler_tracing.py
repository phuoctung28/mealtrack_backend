"""Tests that parse_meal_text_handler emits gen_ai spans for AI calls."""
import json
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from src.app.handlers.command_handlers.parse_meal_text_handler import ParseMealTextHandler
from src.app.commands.meal.parse_meal_text_command import ParseMealTextCommand


def _make_handler():
    """Build ParseMealTextHandler with patched GeminiModelManager."""
    with patch("src.app.handlers.command_handlers.parse_meal_text_handler.GeminiModelManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr_cls.get_instance.return_value = mock_mgr
        handler = ParseMealTextHandler()
        handler._model_manager = mock_mgr
        return handler, mock_mgr


def _mock_span():
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=False)
    return span


def _make_model_mock(content: str = None):
    mock_model = MagicMock()
    mock_model.model = "gemini-2.5-flash"
    mock_response = MagicMock()
    mock_response.content = content or json.dumps({"items": [{"name": "Apple", "quantity": 1, "unit": "piece", "protein": 0, "carbs": 25, "fat": 0, "calories": 95}]})
    mock_response.usage_metadata = {"input_tokens": 150, "output_tokens": 60}
    mock_model.ainvoke = AsyncMock(return_value=mock_response)
    return mock_model, mock_response


@pytest.mark.asyncio
async def test_handle_emits_parse_meal_text_span():
    """handle() emits a gen_ai.request span named 'parse_meal_text'."""
    handler, mock_mgr = _make_handler()
    mock_model, mock_response = _make_model_mock()
    mock_mgr.get_model.return_value = mock_model

    # _fat_secret_service must be patched to avoid real calls
    handler._fat_secret_service = MagicMock()
    handler._fat_secret_service.search_foods = AsyncMock(return_value=[])

    mock_span = _mock_span()
    span_calls = []

    def track_span(op=None, name=None, **kwargs):
        span_calls.append((op, name))
        return mock_span

    with patch("sentry_sdk.start_span", side_effect=track_span):
        cmd = ParseMealTextCommand(user_id="u1", text="apple", language="en")
        await handler.handle(cmd)

    assert ("gen_ai.request", "parse_meal_text") in span_calls


@pytest.mark.asyncio
async def test_handle_sets_model_attribute():
    """handle() sets gen_ai.request.model on the span."""
    handler, mock_mgr = _make_handler()
    mock_model, _ = _make_model_mock()
    mock_mgr.get_model.return_value = mock_model

    handler._fat_secret_service = MagicMock()
    handler._fat_secret_service.search_foods = AsyncMock(return_value=[])

    mock_span = _mock_span()

    with patch("sentry_sdk.start_span", return_value=mock_span):
        cmd = ParseMealTextCommand(user_id="u1", text="apple", language="en")
        await handler.handle(cmd)

    calls = {c.args[0]: c.args[1] for c in mock_span.set_data.call_args_list}
    assert calls.get("gen_ai.request.model") == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_handle_sets_token_attributes():
    """handle() sets gen_ai.usage.input_tokens and output_tokens on the span."""
    handler, mock_mgr = _make_handler()
    mock_model, _ = _make_model_mock()
    mock_mgr.get_model.return_value = mock_model

    handler._fat_secret_service = MagicMock()
    handler._fat_secret_service.search_foods = AsyncMock(return_value=[])

    mock_span = _mock_span()

    with patch("sentry_sdk.start_span", return_value=mock_span):
        cmd = ParseMealTextCommand(user_id="u1", text="apple", language="en")
        await handler.handle(cmd)

    calls = {c.args[0]: c.args[1] for c in mock_span.set_data.call_args_list}
    assert calls.get("gen_ai.usage.input_tokens") == 150
    assert calls.get("gen_ai.usage.output_tokens") == 60


@pytest.mark.asyncio
async def test_translate_meal_names_span_emitted_for_non_english():
    """_translate_english_names() emits a gen_ai.request span named 'translate_meal_names'."""
    handler, mock_mgr = _make_handler()

    # First ainvoke: primary parse — returns an item with an English name
    parse_response = MagicMock()
    parse_response.content = json.dumps({
        "items": [{"name": "Apple", "quantity": 1, "unit": "piece",
                   "protein": 0, "carbs": 25, "fat": 0, "calories": 95}]
    })
    parse_response.usage_metadata = {"input_tokens": 150, "output_tokens": 60}

    # Second ainvoke: translation — returns translated name array
    trans_response = MagicMock()
    trans_response.content = json.dumps(["Táo"])
    trans_response.usage_metadata = {"input_tokens": 50, "output_tokens": 10}

    mock_model = MagicMock()
    mock_model.model = "gemini-2.5-flash"
    mock_model.ainvoke = AsyncMock(side_effect=[parse_response, trans_response])
    mock_mgr.get_model.return_value = mock_model

    handler._fat_secret_service = MagicMock()
    handler._fat_secret_service.search_foods = AsyncMock(return_value=[])

    mock_span = _mock_span()
    span_calls = []

    def track_span(op=None, name=None, **kwargs):
        span_calls.append((op, name))
        return mock_span

    with patch("sentry_sdk.start_span", side_effect=track_span):
        cmd = ParseMealTextCommand(user_id="u1", text="apple", language="vi")
        await handler.handle(cmd)

    assert ("gen_ai.request", "translate_meal_names") in span_calls
