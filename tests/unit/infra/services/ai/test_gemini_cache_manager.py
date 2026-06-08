"""Unit tests for GeminiCacheManager."""

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def stub_google_genai(monkeypatch):
    """Provide a patchable google.genai module when google-genai is not installed."""
    import google

    genai_module = types.ModuleType("google.genai")
    genai_types_module = types.ModuleType("google.genai.types")

    class CreateCachedContentConfig:
        def __init__(self, displayName, contents, ttl, system_instruction=None):
            self.display_name = displayName
            self.contents = contents
            self.ttl = ttl
            self.system_instruction = system_instruction

    genai_types_module.CreateCachedContentConfig = CreateCachedContentConfig
    genai_module.Client = MagicMock()
    genai_module.types = genai_types_module

    monkeypatch.setattr(google, "genai", genai_module, raising=False)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", genai_types_module)


@pytest.fixture
def mock_redis():
    r = MagicMock()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock()
    return r


@pytest.fixture
def cache_manager(mock_redis):
    from src.infra.services.ai.gemini_cache_manager import GeminiCacheManager

    return GeminiCacheManager(redis_client=mock_redis, api_key="test-key")


@pytest.mark.asyncio
async def test_get_cache_name_returns_none_when_no_cache(cache_manager, mock_redis):
    """get_cache_name returns None when Redis has no stored cache name."""
    mock_redis.get.return_value = None
    result = await cache_manager.get_cache_name("recipe")
    assert result is None
    mock_redis.get.assert_awaited_once_with("gemini_cache:recipe")


@pytest.mark.asyncio
async def test_get_cache_name_returns_stored_name(cache_manager, mock_redis):
    """get_cache_name returns the stored cache name when it exists in Redis."""
    mock_redis.get.return_value = "cachedContents/abc123"
    result = await cache_manager.get_cache_name("recipe")
    assert result == "cachedContents/abc123"


@pytest.mark.asyncio
async def test_get_cache_name_for_model_returns_matching_cache(cache_manager, mock_redis):
    """Model-aware lookup returns cache only when metadata matches."""
    mock_redis.get.side_effect = ["cachedContents/abc123", "gemini-2.5-flash-lite"]

    result = await cache_manager.get_cache_name_for_model(
        "recipe", "gemini-2.5-flash-lite"
    )

    assert result == "cachedContents/abc123"


@pytest.mark.asyncio
async def test_get_cache_name_for_model_skips_mismatched_cache(cache_manager, mock_redis):
    """Fallback model must not reuse a cache created for another Gemini model."""
    mock_redis.get.side_effect = ["cachedContents/abc123", "gemini-2.5-flash-lite"]

    result = await cache_manager.get_cache_name_for_model(
        "recipe", "gemini-2.5-flash"
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_cache_name_for_model_skips_legacy_cache(cache_manager, mock_redis):
    """Legacy cache names without model metadata are intentionally not reused."""
    mock_redis.get.side_effect = ["cachedContents/legacy", None]

    result = await cache_manager.get_cache_name_for_model(
        "recipe", "gemini-2.5-flash-lite"
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_cache_name_returns_none_for_unknown_type(cache_manager, mock_redis):
    """get_cache_name returns None for unknown cache types without hitting Redis."""
    result = await cache_manager.get_cache_name("nonexistent_type")
    assert result is None
    mock_redis.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_warm_one_skips_if_already_cached(cache_manager, mock_redis):
    """_warm_one does not call _create_cache when cache already exists in Redis."""
    mock_redis.get.side_effect = ["cachedContents/existing123", "gemini-2.5-flash"]

    with patch.object(
        cache_manager, "_create_cache", new_callable=AsyncMock
    ) as mock_create:
        await cache_manager._warm_one(
            "recipe", "some system prompt", "gemini-2.5-flash"
        )
        mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_warm_one_creates_and_stores_cache(cache_manager, mock_redis):
    """_warm_one calls _create_cache and _set_cache_name when cache is absent."""
    mock_redis.get.return_value = None

    with patch.object(
        cache_manager,
        "_create_cache",
        new_callable=AsyncMock,
        return_value="cachedContents/new456",
    ) as mock_create, patch.object(
        cache_manager, "_set_cache_name", new_callable=AsyncMock
    ) as mock_set:
        await cache_manager._warm_one(
            "recipe", "some system prompt", "gemini-2.5-flash"
        )
        mock_create.assert_awaited_once_with(
            "recipe", "some system prompt", "gemini-2.5-flash"
        )
        mock_set.assert_awaited_once_with(
            "recipe", "cachedContents/new456", "gemini-2.5-flash"
        )


@pytest.mark.asyncio
async def test_warm_one_skips_store_when_create_returns_none(cache_manager, mock_redis):
    """_warm_one does not call _set_cache_name when _create_cache fails (returns None)."""
    mock_redis.get.return_value = None

    with patch.object(
        cache_manager, "_create_cache", new_callable=AsyncMock, return_value=None
    ), patch.object(
        cache_manager, "_set_cache_name", new_callable=AsyncMock
    ) as mock_set:
        await cache_manager._warm_one("vision", "some prompt", "gemini-2.5-flash")
        mock_set.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_cache_name_stores_with_ttl(cache_manager, mock_redis):
    """_set_cache_name stores the cache name with a TTL in Redis."""
    from src.infra.services.ai.gemini_cache_manager import (
        REFRESH_BEFORE_EXPIRY,
        TTL_SECONDS,
    )

    await cache_manager._set_cache_name(
        "recipe", "cachedContents/xyz", "gemini-2.5-flash-lite"
    )
    ttl = TTL_SECONDS + REFRESH_BEFORE_EXPIRY
    assert mock_redis.set.await_count == 2
    mock_redis.set.assert_any_await(
        "gemini_cache:recipe",
        "cachedContents/xyz",
        ex=ttl,
    )
    mock_redis.set.assert_any_await(
        "gemini_cache:recipe:model",
        "gemini-2.5-flash-lite",
        ex=ttl,
    )


@pytest.mark.asyncio
async def test_create_cache_handles_exception_gracefully(cache_manager):
    """_create_cache returns None (not raises) when the Gemini API call fails."""
    mock_client = MagicMock()
    mock_client.caches.create.side_effect = Exception("API error")

    with patch("google.genai.Client", return_value=mock_client):
        result = await cache_manager._create_cache(
            "recipe", "system prompt", "gemini-2.5-flash"
        )

    assert result is None


@pytest.mark.asyncio
async def test_create_cache_uses_google_genai_client(cache_manager):
    """_create_cache creates cached content with the installed google-genai SDK."""
    mock_cache = MagicMock()
    mock_cache.name = "cachedContents/new-sdk"
    mock_client = MagicMock()
    mock_client.models.count_tokens.return_value.total_tokens = 2048
    mock_client.caches.create.return_value = mock_cache

    with patch("google.genai.Client", return_value=mock_client) as client_cls:
        result = await cache_manager._create_cache(
            "recipe", "system prompt", "gemini-2.5-flash"
        )

    assert result == "cachedContents/new-sdk"
    client_cls.assert_called_once_with(api_key="test-key")
    mock_client.models.count_tokens.assert_called_once_with(
        model="gemini-2.5-flash",
        contents="system prompt",
    )
    mock_client.caches.create.assert_called_once()
    _, kwargs = mock_client.caches.create.call_args
    assert kwargs["model"] == "gemini-2.5-flash"
    assert kwargs["config"].display_name == "mealtrack_recipe"
    assert kwargs["config"].contents == "system prompt"
    assert kwargs["config"].system_instruction is None
    assert kwargs["config"].ttl == "3600s"


@pytest.mark.asyncio
async def test_create_cache_skips_content_under_gemini_minimum(cache_manager):
    """_create_cache does not call Gemini cache creation for too-small prompts."""
    mock_cache = MagicMock()
    mock_cache.name = "cachedContents/should-not-create"
    mock_client = MagicMock()
    mock_client.models.count_tokens.return_value.total_tokens = 605
    mock_client.caches.create.return_value = mock_cache

    with patch("google.genai.Client", return_value=mock_client):
        result = await cache_manager._create_cache(
            "text_parse", "short prompt", "gemini-2.5-flash-lite"
        )

    assert result is None
    mock_client.models.count_tokens.assert_called_once_with(
        model="gemini-2.5-flash-lite",
        contents="short prompt",
    )
    mock_client.caches.create.assert_not_called()


@pytest.mark.asyncio
async def test_warm_all_calls_warm_one_for_all_types(cache_manager, mock_redis):
    """warm_all calls _warm_one for each of the 3 cache types (discovery removed as duplicate)."""
    mock_redis.get.return_value = "cachedContents/existing"

    with patch.object(cache_manager, "_warm_one", new_callable=AsyncMock) as mock_warm:
        await cache_manager.warm_all()
        called_types = {call.args[0] for call in mock_warm.call_args_list}
        assert called_types == {"recipe", "vision", "text_parse"}


@pytest.mark.asyncio
async def test_start_refresh_loop_stores_task(cache_manager):
    """start_refresh_loop stores the task handle in _refresh_task."""
    import asyncio

    with patch.object(
        cache_manager, "refresh_loop", new_callable=AsyncMock
    ) as mock_loop:
        mock_loop.return_value = None
        cache_manager.start_refresh_loop()
        assert cache_manager._refresh_task is not None
        # Clean up the task
        cache_manager._refresh_task.cancel()
        try:
            await cache_manager._refresh_task
        except (asyncio.CancelledError, Exception):
            pass


@pytest.mark.asyncio
async def test_stop_cancels_refresh_task(cache_manager):
    """stop() cancels the background refresh task."""
    import asyncio

    async def _long_running():
        await asyncio.sleep(9999)

    cache_manager._refresh_task = asyncio.create_task(_long_running())
    assert not cache_manager._refresh_task.done()

    await cache_manager.stop()
    assert cache_manager._refresh_task.done()


@pytest.mark.asyncio
async def test_stop_is_safe_when_no_task(cache_manager):
    """stop() does nothing (no error) when _refresh_task is None."""
    assert cache_manager._refresh_task is None
    await cache_manager.stop()  # should not raise
