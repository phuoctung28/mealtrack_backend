"""
Gemini API throttle for rate limit management.
Coordinates all Gemini calls via semaphore + cooldown.
"""
import asyncio
import logging
from typing import Optional

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

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None
