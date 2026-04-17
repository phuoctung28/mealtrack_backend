"""Tests that meal_generation_service emits gen_ai spans for each invoke path."""
from unittest.mock import MagicMock, patch

import pytest

from src.infra.adapters.meal_generation_service import MealGenerationService


def _make_service():
    with patch("src.infra.adapters.meal_generation_service.GeminiModelManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr_cls.get_instance.return_value = mock_mgr
        svc = MealGenerationService()
        svc._model_manager = mock_mgr
        return svc, mock_mgr


def _mock_span():
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=False)
    return span


def test_structured_path_emits_span():
    """Structured output path (schema provided) emits a gen_ai.request span."""
    svc, mock_mgr = _make_service()

    mock_llm = MagicMock()
    mock_llm.model = "gemini-2.5-flash"
    mock_llm_structured = MagicMock()
    raw_msg = MagicMock()
    raw_msg.usage_metadata = {"input_tokens": 300, "output_tokens": 100}
    mock_result = {"parsed": MagicMock(), "raw": raw_msg}
    mock_llm_structured.invoke.return_value = mock_result
    mock_llm.with_structured_output.return_value = mock_llm_structured
    mock_mgr.get_model_for_purpose.return_value = mock_llm

    # model_name resolved from env — patch os.getenv to return stable value
    mock_span = _mock_span()
    span_calls = []
    def track_span(op, name):
        span_calls.append((op, name))
        return mock_span

    from pydantic import BaseModel
    class FakeSchema(BaseModel):
        name: str = "test"

    with patch("sentry_sdk.start_span", side_effect=track_span):
        with patch("os.getenv", return_value="gemini-2.5-flash"):
            svc.generate_meal_plan(
                prompt="Generate a meal",
                system_message="You are a nutritionist",
                schema=FakeSchema,
            )

    assert ("gen_ai.request", "meal_generation_structured") in span_calls


def test_legacy_json_path_emits_span():
    """Legacy JSON path (no schema) emits a gen_ai.request span."""
    svc, mock_mgr = _make_service()

    mock_llm = MagicMock()
    mock_llm.model = "gemini-2.5-flash"
    mock_response = MagicMock()
    mock_response.content = '{"meal": "salad"}'
    mock_response.usage_metadata = {"input_tokens": 150, "output_tokens": 50}
    mock_llm.invoke.return_value = mock_response
    mock_mgr.get_model_for_purpose.return_value = mock_llm

    mock_span = _mock_span()
    span_calls = []
    def track_span(op, name):
        span_calls.append((op, name))
        return mock_span

    with patch("sentry_sdk.start_span", side_effect=track_span):
        with patch("os.getenv", return_value="gemini-2.5-flash"):
            svc.generate_meal_plan(
                prompt="Generate a meal",
                system_message="You are a nutritionist",
                response_type="json",
            )

    assert ("gen_ai.request", "meal_generation_legacy_json") in span_calls


def test_structured_path_sets_model_attribute():
    """gen_ai.request.model is set to the resolved model name on the span."""
    svc, mock_mgr = _make_service()

    mock_llm = MagicMock()
    mock_llm.model = "gemini-2.5-flash"
    mock_llm_structured = MagicMock()
    raw_msg = MagicMock()
    raw_msg.usage_metadata = {"input_tokens": 300, "output_tokens": 100}
    mock_result = {"parsed": MagicMock(), "raw": raw_msg}
    mock_llm_structured.invoke.return_value = mock_result
    mock_llm.with_structured_output.return_value = mock_llm_structured
    mock_mgr.get_model_for_purpose.return_value = mock_llm

    mock_span = _mock_span()

    from pydantic import BaseModel
    class FakeSchema(BaseModel):
        name: str = "test"

    with patch("sentry_sdk.start_span", return_value=mock_span):
        with patch("os.getenv", return_value="gemini-2.5-flash"):
            svc.generate_meal_plan(
                prompt="Generate a meal",
                system_message="You are a nutritionist",
                schema=FakeSchema,
            )

    calls = {c.args[0]: c.args[1] for c in mock_span.set_attribute.call_args_list}
    assert calls.get("gen_ai.request.model") == "gemini-2.5-flash"
