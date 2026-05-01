"""Unit tests for Gemini error detection utilities."""


class TestIsRateLimitError:
    """Tests for is_rate_limit_error function."""

    def test_detects_429_in_message(self):
        from src.infra.services.ai.gemini_error_utils import (
            is_rate_limit_error,
        )

        error = Exception("Error 429: Too Many Requests")
        assert is_rate_limit_error(error) is True

    def test_detects_resource_exhausted(self):
        from src.infra.services.ai.gemini_error_utils import (
            is_rate_limit_error,
        )

        error = Exception("ResourceExhausted: quota exceeded")
        assert is_rate_limit_error(error) is True

    def test_detects_503_overloaded(self):
        from src.infra.services.ai.gemini_error_utils import (
            is_rate_limit_error,
        )

        error = Exception("503 Service Unavailable: model overloaded")
        assert is_rate_limit_error(error) is True

    def test_detects_quota_keyword(self):
        from src.infra.services.ai.gemini_error_utils import (
            is_rate_limit_error,
        )

        error = Exception("Quota limit reached for this API")
        assert is_rate_limit_error(error) is True

    def test_ignores_unrelated_errors(self):
        from src.infra.services.ai.gemini_error_utils import (
            is_rate_limit_error,
        )

        error = ValueError("Invalid input format")
        assert is_rate_limit_error(error) is False

    def test_handles_resource_exhausted_exception_type(self):
        from src.infra.services.ai.gemini_error_utils import (
            is_rate_limit_error,
        )
        from google.api_core.exceptions import ResourceExhausted

        error = ResourceExhausted("Quota exceeded")
        assert is_rate_limit_error(error) is True
