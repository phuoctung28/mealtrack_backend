"""Manages Gemini explicit context cache lifecycle."""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

_CACHE_REDIS_KEYS = {
    "recipe": "gemini_cache:recipe",
    "vision": "gemini_cache:vision",
    "text_parse": "gemini_cache:text_parse",
}
_CACHE_MODEL_REDIS_KEYS = {
    cache_type: f"{redis_key}:model"
    for cache_type, redis_key in _CACHE_REDIS_KEYS.items()
}

TTL_SECONDS = 3600
REFRESH_BEFORE_EXPIRY = 600
MIN_CACHE_TOKEN_COUNT = 2048


class GeminiCacheManager:
    """Creates and refreshes Gemini explicit context caches; stores names in Redis."""

    def __init__(self, redis_client, api_key: str | None = None):
        self._redis = redis_client
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self._refresh_task: asyncio.Task | None = None

    async def get_cache_name(self, cache_type: str) -> str | None:
        """Return the Gemini cache name for the given type, or None if not cached."""
        redis_key = _CACHE_REDIS_KEYS.get(cache_type)
        if not redis_key:
            return None
        raw = await self._redis.get(redis_key)
        if raw is None:
            return None
        return raw  # decode_responses=True — already a str

    async def get_cache_name_for_model(self, cache_type: str, model: str) -> str | None:
        """Return the cache name only when it was created for the same model."""
        name = await self.get_cache_name(cache_type)
        if name is None:
            return None

        model_key = _CACHE_MODEL_REDIS_KEYS.get(cache_type)
        if not model_key:
            return None

        cached_model = await self._redis.get(model_key)
        if cached_model == model:
            return name

        logger.info(
            "[GEMINI-CACHE] Skipping cache_type=%s for model=%s: cached_model=%s",
            cache_type,
            model,
            cached_model or "unknown",
        )
        return None

    async def _set_cache_name(self, cache_type: str, name: str, model: str) -> None:
        """Persist Gemini cache metadata to Redis with an extended TTL."""
        redis_key = _CACHE_REDIS_KEYS[cache_type]
        model_key = _CACHE_MODEL_REDIS_KEYS[cache_type]
        ttl = TTL_SECONDS + REFRESH_BEFORE_EXPIRY
        await self._redis.set(redis_key, name, ex=ttl)
        await self._redis.set(model_key, model, ex=ttl)

    async def _create_cache(
        self, cache_type: str, system_prompt: str, model: str
    ) -> str | None:
        """Create a Gemini cached content object and return its name.

        Returns None on any error so callers can fall back to uncached calls.
        """
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self._api_key)
            token_count = await asyncio.to_thread(
                client.models.count_tokens,
                model=model,
                contents=system_prompt,
            )
            total_tokens = token_count.total_tokens or 0
            if total_tokens < MIN_CACHE_TOKEN_COUNT:
                logger.info(
                    "[GEMINI-CACHE] Skipping cache_type=%s: "
                    "total_token_count=%s below minimum=%s",
                    cache_type,
                    total_tokens,
                    MIN_CACHE_TOKEN_COUNT,
                )
                return None

            cache = await asyncio.to_thread(
                client.caches.create,
                model=model,
                config=types.CreateCachedContentConfig(
                    displayName=f"mealtrack_{cache_type}",
                    contents=system_prompt,
                    ttl=f"{TTL_SECONDS}s",
                ),
            )
            logger.info(
                "[GEMINI-CACHE] Created cache_type=%s name=%s", cache_type, cache.name
            )
            return cache.name
        except Exception as e:
            logger.warning(
                "[GEMINI-CACHE] Failed to create cache_type=%s: %s", cache_type, e
            )
            return None

    def wire_to_gemini_service(self) -> None:
        """Inject self into the GeminiService singleton (infra→infra wiring, allowed)."""
        from src.infra.ai.gemini_service import GeminiService  # infra→infra
        GeminiService.get_instance().set_cache_manager(self)
        logger.info("GeminiCacheManager wired into GeminiService")

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
            from src.domain.services.prompts.system_prompts import SystemPrompts

            text_parse_prompt = SystemPrompts.get_meal_text_parsing_prompt()
        except Exception as e:
            logger.warning("[GEMINI-CACHE] Could not load SystemPrompts: %s", e)
            text_parse_prompt = ""

        cache_configs = {
            "recipe": (_get_recipe_prompt(), "gemini-2.5-flash-lite"),
            "vision": (_get_vision_prompt(), "gemini-2.5-flash"),
            "text_parse": (text_parse_prompt, "gemini-2.5-flash-lite"),
        }
        tasks = [
            self._warm_one(ct, prompt, model)
            for ct, (prompt, model) in cache_configs.items()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _warm_one(self, cache_type: str, prompt: str, model: str) -> None:
        """Create and store a single cache if it is not already warm."""
        existing = await self.get_cache_name_for_model(cache_type, model)
        if existing:
            logger.info("[GEMINI-CACHE] Already warm: cache_type=%s", cache_type)
            return
        name = await self._create_cache(cache_type, prompt, model)
        if name:
            await self._set_cache_name(cache_type, name, model)

    async def refresh_loop(self) -> None:
        """Background task: refresh caches before TTL expiry. Run indefinitely."""
        while True:
            await asyncio.sleep(REFRESH_BEFORE_EXPIRY)
            logger.info("[GEMINI-CACHE] Refreshing caches before TTL expiry")
            # Clear stale Redis entries so _warm_one creates fresh caches
            for redis_key in [*_CACHE_REDIS_KEYS.values(), *_CACHE_MODEL_REDIS_KEYS.values()]:
                try:
                    await self._redis.delete(redis_key)
                except Exception as e:
                    logger.warning(
                        "[GEMINI-CACHE] Failed to clear Redis key %s: %s", redis_key, e
                    )
            await self.warm_all()


# ---------------------------------------------------------------------------
# Helper accessors — isolated so that import failures affect only warm_all
# ---------------------------------------------------------------------------


def _get_recipe_prompt() -> str:
    try:
        from src.domain.services.prompts.system_prompts import SystemPrompts

        return SystemPrompts.RECIPE_GENERATION
    except Exception:
        return ""


def _get_vision_prompt() -> str:
    try:
        from src.domain.services.prompts.system_prompts import SystemPrompts

        return SystemPrompts.VISION_ANALYSIS
    except Exception:
        return ""
