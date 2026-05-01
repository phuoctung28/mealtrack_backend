"""
Gemini API throttle for rate limit management.
Coordinates all Gemini calls via semaphore + cooldown.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONCURRENT = 4
DEFAULT_COOLDOWN_SECONDS = 3


class GeminiThrottle:
    """
    Singleton throttle for Gemini API calls.

    - Semaphore limits concurrent calls (default: 4)
    - Cooldown blocks all calls briefly after rate limit detected
    """

    _instance: Optional["GeminiThrottle"] = None

    def __init__(self, max_concurrent: int = DEFAULT_MAX_CONCURRENT):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cooldown_until: float = 0
        self._lock = asyncio.Lock()
        self._max_concurrent = max_concurrent

    @classmethod
    def get_instance(
        cls, max_concurrent: int = DEFAULT_MAX_CONCURRENT
    ) -> "GeminiThrottle":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls(max_concurrent)
        return cls._instance

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        """
        Acquire throttle before making Gemini API call.

        Waits for:
        1. Cooldown to expire (if active)
        2. Semaphore slot to become available
        """
        # Wait for cooldown if active
        async with self._lock:
            wait_time = self._cooldown_until - time.time()

        if wait_time > 0:
            logger.info(f"[THROTTLE] Waiting {wait_time:.2f}s for cooldown")
            await asyncio.sleep(wait_time)

        # Acquire semaphore
        async with self._semaphore:
            yield

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None
