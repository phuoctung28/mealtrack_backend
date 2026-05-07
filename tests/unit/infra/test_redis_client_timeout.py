"""Unit test: RedisClient ConnectionPool must include socket timeouts."""

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
