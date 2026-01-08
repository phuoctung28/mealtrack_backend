"""
Unit tests for enhanced cache decorators.
"""
from unittest.mock import AsyncMock

import pytest

from src.infra.cache.decorators import (
    cached,
    cached_method,
    invalidate_on_write,
    CacheTTL,
)


@pytest.fixture
def mock_cache_service():
    """Create mock cache service."""
    service = AsyncMock()
    service.get_json = AsyncMock(return_value=None)
    service.set_json = AsyncMock(return_value=True)
    service.invalidate = AsyncMock(return_value=True)
    service.invalidate_pattern = AsyncMock(return_value=1)
    return service


class MockService:
    """Test service for decorator testing."""
    
    def __init__(self, cache_service):
        self.cache_service = cache_service
        self.call_count = 0
    
    @cached(
        key_func=lambda self, user_id: f"user:{user_id}",
        ttl=3600
    )
    async def get_user(self, user_id: str) -> dict:
        self.call_count += 1
        return {"id": user_id, "name": "Test User"}
    
    @cached_method(prefix="data", ttl=CacheTTL.MEDIUM)
    async def get_data(self, key: str) -> dict:
        self.call_count += 1
        return {"key": key, "value": "test"}
    
    @invalidate_on_write(
        key_patterns=lambda self, user_id, *args, **kwargs: [f"user:{user_id}"]
    )
    async def update_user(self, user_id: str, data: dict) -> bool:
        self.call_count += 1
        return True


class TestCachedDecorator:
    """Test @cached decorator."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_value(self, mock_cache_service):
        """Should return cached value on cache hit."""
        mock_cache_service.get_json.return_value = {"id": "123", "cached": True}
        
        service = MockService(mock_cache_service)
        result = await service.get_user("123")
        
        assert result == {"id": "123", "cached": True}
        assert service.call_count == 0  # Method not called
        mock_cache_service.get_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_calls_method(self, mock_cache_service):
        """Should call method on cache miss."""
        mock_cache_service.get_json.return_value = None
        
        service = MockService(mock_cache_service)
        result = await service.get_user("123")
        
        assert result == {"id": "123", "name": "Test User"}
        assert service.call_count == 1
        mock_cache_service.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_stores_result(self, mock_cache_service):
        """Should store result in cache on miss."""
        mock_cache_service.get_json.return_value = None
        
        service = MockService(mock_cache_service)
        await service.get_user("123")
        
        # Verify set_json was called with correct key and TTL
        call_args = mock_cache_service.set_json.call_args
        assert call_args[0][0] == "user:123"
        assert call_args[0][2] == 3600

    @pytest.mark.asyncio
    async def test_no_cache_service_calls_method(self):
        """Should call method directly if no cache service."""
        service = MockService(cache_service=None)
        result = await service.get_user("123")
        
        assert result == {"id": "123", "name": "Test User"}
        assert service.call_count == 1


class TestCachedMethodDecorator:
    """Test @cached_method decorator."""

    @pytest.mark.asyncio
    async def test_auto_generates_cache_key(self, mock_cache_service):
        """Should auto-generate cache key from args."""
        mock_cache_service.get_json.return_value = None
        
        service = MockService(mock_cache_service)
        await service.get_data("test_key")
        
        # Key should start with prefix
        call_args = mock_cache_service.set_json.call_args
        assert call_args[0][0].startswith("data:")

    @pytest.mark.asyncio
    async def test_different_args_different_keys(self, mock_cache_service):
        """Different args should generate different cache keys."""
        mock_cache_service.get_json.return_value = None
        
        service = MockService(mock_cache_service)
        await service.get_data("key1")
        await service.get_data("key2")
        
        # Should have different keys
        calls = mock_cache_service.set_json.call_args_list
        key1 = calls[0][0][0]
        key2 = calls[1][0][0]
        assert key1 != key2


class TestInvalidateOnWrite:
    """Test @invalidate_on_write decorator."""

    @pytest.mark.asyncio
    async def test_invalidates_after_write(self, mock_cache_service):
        """Should invalidate cache after write operation."""
        service = MockService(mock_cache_service)
        result = await service.update_user("123", {"name": "Updated"})
        
        assert result is True
        assert service.call_count == 1
        mock_cache_service.invalidate.assert_called_once_with("user:123")

    @pytest.mark.asyncio
    async def test_write_succeeds_even_if_invalidation_fails(self, mock_cache_service):
        """Write should succeed even if cache invalidation fails."""
        mock_cache_service.invalidate.side_effect = Exception("Redis error")
        
        service = MockService(mock_cache_service)
        result = await service.update_user("123", {"name": "Updated"})
        
        assert result is True  # Write succeeded


class TestCacheTTL:
    """Test TTL constants."""

    def test_ttl_values(self):
        """TTL values should be reasonable."""
        assert CacheTTL.VERY_SHORT == 60
        assert CacheTTL.SHORT == 300
        assert CacheTTL.MEDIUM == 3600
        assert CacheTTL.LONG == 86400
        assert CacheTTL.VERY_LONG == 604800
        assert CacheTTL.PERMANENT == 2592000

    def test_ttl_ordering(self):
        """TTL values should be in ascending order."""
        assert CacheTTL.VERY_SHORT < CacheTTL.SHORT
        assert CacheTTL.SHORT < CacheTTL.MEDIUM
        assert CacheTTL.MEDIUM < CacheTTL.LONG
        assert CacheTTL.LONG < CacheTTL.VERY_LONG
        assert CacheTTL.VERY_LONG < CacheTTL.PERMANENT
