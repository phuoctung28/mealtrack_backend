"""Manages Gemini explicit context cache lifecycle."""
import asyncio
import datetime
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_REDIS_KEYS = {
    "recipe":     "gemini_cache:recipe",
    "vision":     "gemini_cache:vision",
    "text_parse": "gemini_cache:text_parse",
}

TTL_SECONDS = 3600
REFRESH_BEFORE_EXPIRY = 600


class GeminiCacheManager:
    """Creates and refreshes Gemini explicit context caches; stores names in Redis."""

    def __init__(self, redis_client, api_key: Optional[str] = None):
        self._redis = redis_client
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self._refresh_task: Optional[asyncio.Task] = None

    async def get_cache_name(self, cache_type: str) -> Optional[str]:
        """Return the Gemini cache name for the given type, or None if not cached."""
        redis_key = _CACHE_REDIS_KEYS.get(cache_type)
        if not redis_key:
            return None
        raw = await self._redis.get(redis_key)
        if raw is None:
            return None
        return raw  # decode_responses=True — already a str

    async def _set_cache_name(self, cache_type: str, name: str) -> None:
        """Persist a Gemini cache name to Redis with an extended TTL."""
        redis_key = _CACHE_REDIS_KEYS[cache_type]
        await self._redis.set(redis_key, name, ex=TTL_SECONDS + REFRESH_BEFORE_EXPIRY)

    async def _create_cache(self, cache_type: str, system_prompt: str, model: str) -> Optional[str]:
        """Create a Gemini cached content object and return its name.

        Returns None on any error so callers can fall back to uncached calls.
        """
        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            cache = await asyncio.to_thread(
                genai.caching.CachedContent.create,
                model=f"models/{model}",
                display_name=f"mealtrack_{cache_type}",
                system_instruction=system_prompt,
                ttl=datetime.timedelta(seconds=TTL_SECONDS),
            )
            logger.info("[GEMINI-CACHE] Created cache_type=%s name=%s", cache_type, cache.name)
            return cache.name
        except Exception as e:
            logger.warning("[GEMINI-CACHE] Failed to create cache_type=%s: %s", cache_type, e)
            return None

    def start_refresh_loop(self) -> None:
        """Schedule the background refresh loop as a managed asyncio task."""
        self._refresh_task = asyncio.create_task(self.refresh_loop())

    async def stop(self) -> None:
        """Cancel the background refresh task and wait for it to finish."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

    async def warm_all(self) -> None:
        """Warm all 3 context caches concurrently.

        Uses SystemPrompts constants; falls back gracefully if any creation fails.
        """
        try:
            from src.infra.services.ai.prompts.system_prompts import SystemPrompts

            text_parse_prompt = SystemPrompts.get_meal_text_parsing_prompt()
        except Exception as e:
            logger.warning("[GEMINI-CACHE] Could not load SystemPrompts: %s", e)
            text_parse_prompt = ""

        cache_configs = {
            "recipe":     (_get_recipe_prompt(), "gemini-2.5-flash-lite"),
            "vision":     (_get_vision_prompt(), "gemini-2.5-flash"),
            "text_parse": (text_parse_prompt,    "gemini-2.5-flash-lite"),
        }
        tasks = [
            self._warm_one(ct, prompt, model)
            for ct, (prompt, model) in cache_configs.items()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _warm_one(self, cache_type: str, prompt: str, model: str) -> None:
        """Create and store a single cache if it is not already warm."""
        existing = await self.get_cache_name(cache_type)
        if existing:
            logger.info("[GEMINI-CACHE] Already warm: cache_type=%s", cache_type)
            return
        name = await self._create_cache(cache_type, prompt, model)
        if name:
            await self._set_cache_name(cache_type, name)

    async def refresh_loop(self) -> None:
        """Background task: refresh caches before TTL expiry. Run indefinitely."""
        while True:
            await asyncio.sleep(REFRESH_BEFORE_EXPIRY)
            logger.info("[GEMINI-CACHE] Refreshing caches before TTL expiry")
            # Clear stale Redis entries so _warm_one creates fresh caches
            for redis_key in _CACHE_REDIS_KEYS.values():
                try:
                    await self._redis.delete(redis_key)
                except Exception as e:
                    logger.warning("[GEMINI-CACHE] Failed to clear Redis key %s: %s", redis_key, e)
            await self.warm_all()


# ---------------------------------------------------------------------------
# Helper accessors — isolated so that import failures affect only warm_all
# ---------------------------------------------------------------------------

def _get_recipe_prompt() -> str:
    try:
        from src.infra.services.ai.prompts.system_prompts import SystemPrompts
        return SystemPrompts.RECIPE_GENERATION
    except Exception:
        return ""


def _get_vision_prompt() -> str:
    try:
        from src.infra.services.ai.prompts.system_prompts import SystemPrompts
        return SystemPrompts.VISION_ANALYSIS
    except Exception:
        return ""
