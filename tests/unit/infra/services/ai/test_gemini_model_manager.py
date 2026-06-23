"""Tests that GeminiService model pool honours timeout and retry env vars."""

from unittest.mock import Mock, patch

import pytest


def test_created_gemini_models_use_bounded_timeout_and_retries(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "7.5")
    monkeypatch.setenv("GEMINI_MAX_RETRIES", "2")

    from src.infra.ai.gemini_service import GeminiService

    GeminiService.reset_instance()
    svc = GeminiService()

    with patch("langchain_google_genai.ChatGoogleGenerativeAI") as model_cls:
        model_cls.return_value = Mock()
        # Trigger model creation through the pool
        svc._get_model(
            model_name="gemini-2.5-flash-lite",
            purpose_hint="general",
            response_mime_type="application/json",
        )

    call_kwargs = model_cls.call_args.kwargs
    assert call_kwargs["request_timeout"] == 7.5
    assert call_kwargs["retries"] == 2

    GeminiService.reset_instance()
