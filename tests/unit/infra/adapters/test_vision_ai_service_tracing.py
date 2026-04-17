"""
Tests for Sentry gen_ai span instrumentation in VisionAIService.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.infra.adapters.vision_ai_service import VisionAIService


def _make_service_and_model():
    """
    Build a VisionAIService with all external dependencies patched out.
    Returns (svc, mock_model).
    """
    with patch("src.infra.adapters.vision_ai_service.GeminiModelManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_model = MagicMock()
        mock_model.model = "gemini-2.5-flash"

        mock_mgr.get_instance.return_value = mock_mgr
        mock_mgr.get_model.return_value = mock_model
        mock_mgr_cls.get_instance.return_value = mock_mgr

        svc = VisionAIService()

    # After __init__ the svc.model is already set to mock_model
    return svc, mock_model


def _make_mock_response():
    mock_response = MagicMock()
    mock_response.content = '{"dish_name": "salad", "ingredients": []}'
    mock_response.usage_metadata = {"input_tokens": 200, "output_tokens": 80}
    return mock_response


def test_analyze_emits_gen_ai_span():
    """VisionAIService._analyze_image_reference must start a span with op='gen_ai.request' and name='vision_analysis'."""
    svc, mock_model = _make_service_and_model()
    mock_model.invoke.return_value = _make_mock_response()

    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)

    strategy = MagicMock()
    strategy.get_analysis_prompt.return_value = "Analyze this food."
    strategy.get_user_message.return_value = "What is this?"
    strategy.get_strategy_name.return_value = "basic"

    with patch("sentry_sdk.start_span", return_value=mock_span) as mock_start:
        svc._analyze_image_reference("https://example.com/food.jpg", strategy)

    mock_start.assert_called_once()
    call_kwargs = mock_start.call_args
    # Accept both positional and keyword arguments
    args, kwargs = call_kwargs
    assert kwargs.get("op") == "gen_ai.request" or (len(args) >= 1 and args[0] == "gen_ai.request"), \
        f"Expected op='gen_ai.request', got call: {call_kwargs}"
    assert kwargs.get("name") == "vision_analysis" or (len(args) >= 2 and args[1] == "vision_analysis"), \
        f"Expected name='vision_analysis', got call: {call_kwargs}"


def test_analyze_sets_model_attribute():
    """VisionAIService._analyze_image_reference must set gen_ai.request.model on the span."""
    svc, mock_model = _make_service_and_model()
    mock_model.model = "gemini-2.5-flash"
    mock_model.invoke.return_value = _make_mock_response()

    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)

    strategy = MagicMock()
    strategy.get_analysis_prompt.return_value = "Analyze this food."
    strategy.get_user_message.return_value = "What is this?"
    strategy.get_strategy_name.return_value = "basic"

    with patch("sentry_sdk.start_span", return_value=mock_span) as mock_start:
        svc._analyze_image_reference("https://example.com/food.jpg", strategy)

    # Verify gen_ai.request.model was set
    set_attribute_calls = mock_span.set_attribute.call_args_list
    attribute_names = [call.args[0] for call in set_attribute_calls]
    assert "gen_ai.request.model" in attribute_names, \
        f"Expected 'gen_ai.request.model' to be set. Actual calls: {set_attribute_calls}"

    # Verify the value matches the model name
    for call in set_attribute_calls:
        if call.args[0] == "gen_ai.request.model":
            assert call.args[1] == "gemini-2.5-flash", \
                f"Expected model name 'gemini-2.5-flash', got: {call.args[1]}"
