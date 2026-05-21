"""Unit tests for GeminiCacheManager."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


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
async def test_get_cache_name_returns_none_for_unknown_type(cache_manager, mock_redis):
    """get_cache_name returns None for unknown cache types without hitting Redis."""
    result = await cache_manager.get_cache_name("nonexistent_type")
    assert result is None
    mock_redis.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_warm_one_skips_if_already_cached(cache_manager, mock_redis):
    """_warm_one does not call _create_cache when cache already exists in Redis."""
    mock_redis.get.return_value = "cachedContents/existing123"

    with patch.object(cache_manager, "_create_cache", new_callable=AsyncMock) as mock_create:
        await cache_manager._warm_one("recipe", "some system prompt", "gemini-2.5-flash")
        mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_warm_one_creates_and_stores_cache(cache_manager, mock_redis):
    """_warm_one calls _create_cache and _set_cache_name when cache is absent."""
    mock_redis.get.return_value = None

    with patch.object(
        cache_manager, "_create_cache", new_callable=AsyncMock, return_value="cachedContents/new456"
    ) as mock_create, patch.object(
        cache_manager, "_set_cache_name", new_callable=AsyncMock
    ) as mock_set:
        await cache_manager._warm_one("recipe", "some system prompt", "gemini-2.5-flash")
        mock_create.assert_awaited_once_with("recipe", "some system prompt", "gemini-2.5-flash")
        mock_set.assert_awaited_once_with("recipe", "cachedContents/new456")


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
    from src.infra.services.ai.gemini_cache_manager import TTL_SECONDS, REFRESH_BEFORE_EXPIRY

    await cache_manager._set_cache_name("recipe", "cachedContents/xyz")
    mock_redis.set.assert_awaited_once_with(
        "gemini_cache:recipe", "cachedContents/xyz", ex=TTL_SECONDS + REFRESH_BEFORE_EXPIRY
    )


@pytest.mark.asyncio
async def test_create_cache_handles_exception_gracefully(cache_manager):
    """_create_cache returns None (not raises) when the Gemini API call fails."""
    # Patch the import inside _create_cache so the test works without google-generativeai installed
    mock_genai = MagicMock()
    mock_genai.caching.CachedContent.create.side_effect = Exception("API error")
    with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
        result = await cache_manager._create_cache("recipe", "system prompt", "gemini-2.5-flash")
    assert result is None


@pytest.mark.asyncio
async def test_warm_all_calls_warm_one_for_all_types(cache_manager, mock_redis):
    """warm_all calls _warm_one for each of the 4 cache types."""
    mock_redis.get.return_value = "cachedContents/existing"

    with patch.object(cache_manager, "_warm_one", new_callable=AsyncMock) as mock_warm:
        await cache_manager.warm_all()
        called_types = {call.args[0] for call in mock_warm.call_args_list}
        assert called_types == {"recipe", "vision", "discovery", "text_parse"}
