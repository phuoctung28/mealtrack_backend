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


import asyncio  # noqa: E402


class TestGeminiThrottleSemaphore:
    """Tests for semaphore concurrency limiting."""

    @pytest.fixture(autouse=True)
    def reset_throttle(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle
        GeminiThrottle.reset()
        yield
        GeminiThrottle.reset()

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        throttle = GeminiThrottle.get_instance(max_concurrent=2)
        active_count = 0
        max_observed = 0
        results = []

        async def task(task_id: int):
            nonlocal active_count, max_observed
            async with throttle.acquire():
                active_count += 1
                max_observed = max(max_observed, active_count)
                await asyncio.sleep(0.1)
                active_count -= 1
                results.append(task_id)

        await asyncio.gather(*[task(i) for i in range(6)])

        assert max_observed <= 2, (
            f"Expected max 2 concurrent, got {max_observed}"
        )
        assert len(results) == 6, "All tasks should complete"

    @pytest.mark.asyncio
    async def test_acquire_releases_on_exception(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        throttle = GeminiThrottle.get_instance(max_concurrent=1)

        with pytest.raises(ValueError):
            async with throttle.acquire():
                raise ValueError("test error")

        # Should be able to acquire again
        async with throttle.acquire():
            pass  # Success if we get here
