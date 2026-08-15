"""Redis-backed shared provider budget."""

import time

from src.domain.ports.provider_budget_port import ProviderBudgetPort
from src.infra.cache.redis_client import RedisClient


class RedisProviderBudget(ProviderBudgetPort):
    """Count provider calls in a short shared window and fail closed on Redis errors."""

    def __init__(self, redis_client: RedisClient, window_seconds: int = 60):
        self.redis = redis_client
        self.window_seconds = window_seconds

    async def acquire(self, namespace: str, limit: int) -> bool:
        if limit < 1:
            return False
        window = int(time.time() // self.window_seconds)
        key = f"nutrition:provider-budget:v1:{namespace}:{window}"
        count = await self.redis.incr_with_expiry(key, self.window_seconds + 1)
        return count is not None and count <= limit
