from unittest.mock import Mock, patch

from src.infra.services.ai.gemini_model_manager import GeminiModelManager


def test_created_gemini_models_use_bounded_timeout_and_retries(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "7.5")
    monkeypatch.setenv("GEMINI_MAX_RETRIES", "2")

    manager = GeminiModelManager.get_instance()

    with patch("langchain_google_genai.ChatGoogleGenerativeAI") as model_cls:
        model_cls.return_value = Mock()

        manager.get_model(response_mime_type="application/json")

    call_kwargs = model_cls.call_args.kwargs
    assert call_kwargs["request_timeout"] == 7.5
    assert call_kwargs["retries"] == 2
