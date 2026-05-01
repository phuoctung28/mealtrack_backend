"""Unit tests for GeminiThrottle."""
import pytest


class TestGeminiThrottleSingleton:
    """Tests for singleton behavior."""

    @pytest.fixture(autouse=True)
    def reset_throttle(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle
        GeminiThrottle.reset()
        yield
        GeminiThrottle.reset()

    def test_get_instance_returns_same_object(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        instance1 = GeminiThrottle.get_instance()
        instance2 = GeminiThrottle.get_instance()

        assert instance1 is instance2

    def test_reset_clears_instance(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        instance1 = GeminiThrottle.get_instance()
        GeminiThrottle.reset()
        instance2 = GeminiThrottle.get_instance()

        assert instance1 is not instance2
