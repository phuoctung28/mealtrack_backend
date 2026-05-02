"""Integration tests for Gemini rate limit handling."""
import asyncio
import pytest
import time

from src.infra.services.ai.gemini_throttle import GeminiThrottle


class TestGeminiRateLimitIntegration:
    """Integration tests for the full rate limit handling flow."""

    @pytest.fixture(autouse=True)
    def reset_throttle(self):
        GeminiThrottle.reset()
        yield
        GeminiThrottle.reset()

    @pytest.mark.asyncio
    async def test_throttle_limits_concurrent_recipe_generation(self):
        """Verify throttle limits concurrent calls to 4."""
        throttle = GeminiThrottle.get_instance(max_concurrent=4)

        active = 0
        max_active = 0

        async def mock_generate():
            nonlocal active, max_active
            async with throttle.acquire():
                active += 1
                max_active = max(max_active, active)
                await asyncio.sleep(0.05)
                active -= 1
                return {"ingredients": [], "recipe_steps": []}

        # Simulate 7 parallel recipe tasks
        tasks = [asyncio.create_task(mock_generate()) for _ in range(7)]
        await asyncio.gather(*tasks)

        assert max_active <= 4, f"Max concurrent should be 4, got {max_active}"

    @pytest.mark.asyncio
    async def test_rate_limit_triggers_cooldown_for_other_requests(self):
        """Verify that rate limit on one request slows down others."""
        throttle = GeminiThrottle.get_instance(max_concurrent=4)

        # Simulate first request hitting rate limit
        throttle.record_rate_limit(retry_after=1)

        # Second request should wait for cooldown
        start = time.time()
        async with throttle.acquire():
            elapsed = time.time() - start

        assert elapsed >= 0.9, f"Should wait ~1s, waited {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_graceful_degradation_returns_partial_results(self):
        """Verify partial results returned when some tasks fail."""
        throttle = GeminiThrottle.get_instance(max_concurrent=4)

        async def task(task_id: int, should_fail: bool):
            async with throttle.acquire():
                if should_fail:
                    throttle.record_rate_limit(retry_after=1)
                    return None
                return {"id": task_id}

        # Simulate 7 tasks, 2 fail
        tasks = [
            asyncio.create_task(task(i, i in [2, 5]))
            for i in range(7)
        ]
        results = await asyncio.gather(*tasks)

        successful = [r for r in results if r is not None]
        assert len(successful) == 5, (
            f"Expected 5 successes, got {len(successful)}"
        )
