"""Unit test: RedisClient ConnectionPool must include socket timeouts."""

import pytest
from unittest.mock import patch, MagicMock

from src.infra.cache.redis_client import RedisClient


def test_connection_pool_has_socket_timeout():
    """ConnectionPool.from_url must be called with socket_timeout."""
    with patch(
        "src.infra.cache.redis_client.redis.ConnectionPool.from_url"
    ) as mock_from_url:
        mock_from_url.return_value = MagicMock()
        RedisClient(redis_url="redis://localhost:6379")
        call_kwargs = mock_from_url.call_args[1]
        assert "socket_timeout" in call_kwargs, "socket_timeout must be set"
        assert (
            "socket_connect_timeout" in call_kwargs
        ), "socket_connect_timeout must be set"
        assert call_kwargs["socket_timeout"] > 0
        assert call_kwargs["socket_connect_timeout"] > 0


def test_connection_pool_timeout_is_reasonable():
    """socket_timeout should be <= 10 seconds to avoid blocking too long."""
    with patch(
        "src.infra.cache.redis_client.redis.ConnectionPool.from_url"
    ) as mock_from_url:
        mock_from_url.return_value = MagicMock()
        RedisClient(redis_url="redis://localhost:6379")
        call_kwargs = mock_from_url.call_args[1]
        assert call_kwargs["socket_timeout"] <= 10.0
        assert call_kwargs["socket_connect_timeout"] <= 10.0


def test_connection_pool_timeout_custom_value():
    """Custom timeout values must be forwarded to the pool."""
    with patch(
        "src.infra.cache.redis_client.redis.ConnectionPool.from_url"
    ) as mock_from_url:
        mock_from_url.return_value = MagicMock()
        RedisClient(
            redis_url="redis://localhost:6379",
            socket_timeout=1.5,
            socket_connect_timeout=2.5,
        )
        call_kwargs = mock_from_url.call_args[1]
        assert call_kwargs["socket_timeout"] == 1.5
        assert call_kwargs["socket_connect_timeout"] == 2.5


@pytest.mark.asyncio
async def test_delete_pattern_uses_scan_not_keys():
    """delete_pattern must use scan_iter, never client.keys (blocking)."""
    from src.infra.cache.redis_client import RedisClient
    from unittest.mock import AsyncMock

    client = RedisClient.__new__(RedisClient)

    deleted_keys = []

    async def fake_scan_iter(match):
        for k in ["user:abc:macros:2026-01-01", "user:abc:macros:2026-01-02"]:
            yield k

    mock_client = AsyncMock()
    mock_client.scan_iter = fake_scan_iter
    mock_client.delete = AsyncMock(side_effect=lambda k: deleted_keys.append(k))
    client.client = mock_client

    count = await client.delete_pattern("user:abc:macros:*")

    assert count == 2
    assert "user:abc:macros:2026-01-01" in deleted_keys
    assert "user:abc:macros:2026-01-02" in deleted_keys
    assert mock_client.keys.call_count == 0  # must NOT use blocking KEYS
