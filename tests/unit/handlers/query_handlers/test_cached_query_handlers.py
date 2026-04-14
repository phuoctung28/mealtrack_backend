"""
Unit tests for cache hit/miss behaviour on query handlers that use Redis.
All tests use a mock CacheService — no real Redis required.
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.domain.cache.cache_keys import CacheKeys
from src.app.queries.tdee import GetUserTdeeQuery


class TestGetUserTdeeQueryHandlerCache:
    """Cache behaviour for GetUserTdeeQueryHandler."""

    @pytest.mark.asyncio
    async def test_returns_cached_value_on_hit(self):
        """On a Redis cache hit the DB is never touched."""
        from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler

        cached_payload = {"user_id": "u1", "tdee": 2000.0, "bmr": 1700.0}
        cache_service = MagicMock()
        cache_service.get_json = AsyncMock(return_value=cached_payload)
        cache_service.set_json = AsyncMock()

        handler = GetUserTdeeQueryHandler(cache_service=cache_service)
        query = GetUserTdeeQuery(user_id="u1")

        result = await handler.handle(query)

        assert result == cached_payload
        cache_service.get_json.assert_awaited_once()
        cache_service.set_json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_stores_result_in_cache_on_miss(self):
        """On a Redis cache miss the result is stored for next time."""
        from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler

        db_result = {"user_id": "u1", "tdee": 2000.0, "bmr": 1700.0, "macros": {}}
        cache_service = MagicMock()
        cache_service.get_json = AsyncMock(return_value=None)  # miss
        cache_service.set_json = AsyncMock()

        handler = GetUserTdeeQueryHandler(cache_service=cache_service)
        query = GetUserTdeeQuery(user_id="u1")

        with patch.object(handler, '_compute_tdee', AsyncMock(return_value=db_result)):
            result = await handler.handle(query)

        assert result == db_result
        cache_service.set_json.assert_awaited_once()
        # Verify the cache key used
        call_args = cache_service.set_json.call_args
        expected_key, _ = CacheKeys.user_tdee("u1")
        assert call_args[0][0] == expected_key

    @pytest.mark.asyncio
    async def test_works_without_cache_service(self):
        """Handler works normally when no cache_service provided."""
        from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler

        db_result = {"user_id": "u1", "tdee": 2000.0}
        handler = GetUserTdeeQueryHandler()  # no cache_service
        query = GetUserTdeeQuery(user_id="u1")

        with patch.object(handler, '_compute_tdee', AsyncMock(return_value=db_result)):
            result = await handler.handle(query)

        assert result == db_result
