"""Unit tests for MealGenerationService rate limit handling."""
import pytest
from unittest.mock import MagicMock, patch

from src.api.exceptions import ExternalServiceException


class TestMealGenerationServiceResilience:
    """Tests for rate limit retry logic."""

    @pytest.fixture
    def mock_model_manager(self):
        manager = MagicMock()
        manager.model_name = "gemini-test"
        mock_llm = MagicMock()
        manager.get_model_for_purpose.return_value = mock_llm
        manager.get_model.return_value = mock_llm
        return manager

    @pytest.fixture
    def service(self, mock_model_manager):
        from src.infra.adapters.meal_generation_service import MealGenerationService

        with patch.object(
            MealGenerationService, '__init__', lambda self: None
        ):
            svc = MealGenerationService()
            svc._model_manager = mock_model_manager
            return svc

    def test_retries_once_on_resource_exhausted(self, service, mock_model_manager):
        from google.api_core.exceptions import ResourceExhausted

        mock_llm = mock_model_manager.get_model_for_purpose.return_value

        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.content = '{"meal_name": "Test Meal"}'
        mock_llm.invoke.side_effect = [
            ResourceExhausted("Quota exceeded"),
            mock_response,
        ]

        result = service.generate_meal_plan(
            prompt="test prompt",
            system_message="test system",
            response_type="json",
        )

        assert mock_llm.invoke.call_count == 2
        assert result == {"meal_name": "Test Meal"}

    def test_raises_external_service_exception_after_retry_fails(
        self, service, mock_model_manager
    ):
        from google.api_core.exceptions import ResourceExhausted

        mock_llm = mock_model_manager.get_model_for_purpose.return_value
        mock_llm.invoke.side_effect = ResourceExhausted("Quota exceeded")

        with pytest.raises(ExternalServiceException) as exc_info:
            service.generate_meal_plan(
                prompt="test prompt",
                system_message="test system",
                response_type="json",
            )

        assert exc_info.value.error_code == "AI_RATE_LIMITED"
        assert exc_info.value.details["retry_after_seconds"] == 5
        assert mock_llm.invoke.call_count == 2

    def test_non_rate_limit_error_propagates_immediately(
        self, service, mock_model_manager
    ):
        mock_llm = mock_model_manager.get_model_for_purpose.return_value
        mock_llm.invoke.side_effect = ValueError("Invalid input")

        with pytest.raises(ValueError, match="Invalid input"):
            service.generate_meal_plan(
                prompt="test prompt",
                system_message="test system",
                response_type="json",
            )

        assert mock_llm.invoke.call_count == 1
