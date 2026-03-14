"""Unit tests for queue client factory provider resolution."""

import pytest

from src.infra.cache.redis_client import RedisClient
from src.infra.queue.queue_client_factory import create_queue_redis_client


@pytest.mark.unit
def test_upstash_provider_requires_url(monkeypatch):
    """Upstash provider must have UPSTASH_REDIS_URL set."""
    monkeypatch.setattr(
        "src.infra.queue.queue_client_factory.settings",
        type("S", (), {
            "QUEUE_PROVIDER": "upstash",
            "UPSTASH_REDIS_URL": None,
            "DEDICATED_REDIS_URL": None,
            "REDIS_MAX_CONNECTIONS": 10,
        })(),
    )
    with pytest.raises(ValueError, match="UPSTASH_REDIS_URL"):
        create_queue_redis_client()


@pytest.mark.unit
def test_upstash_provider_rejects_empty_url(monkeypatch):
    """Upstash provider rejects empty string URL."""
    monkeypatch.setattr(
        "src.infra.queue.queue_client_factory.settings",
        type("S", (), {
            "QUEUE_PROVIDER": "upstash",
            "UPSTASH_REDIS_URL": "  ",
            "DEDICATED_REDIS_URL": None,
            "REDIS_MAX_CONNECTIONS": 10,
        })(),
    )
    with pytest.raises(ValueError, match="UPSTASH_REDIS_URL"):
        create_queue_redis_client()


@pytest.mark.unit
def test_upstash_provider_returns_client(monkeypatch):
    """Upstash provider returns RedisClient with given URL."""
    monkeypatch.setattr(
        "src.infra.queue.queue_client_factory.settings",
        type("S", (), {
            "QUEUE_PROVIDER": "upstash",
            "UPSTASH_REDIS_URL": "rediss://default:xxx@us1-xxx.upstash.io:6379",
            "DEDICATED_REDIS_URL": None,
            "REDIS_MAX_CONNECTIONS": 20,
        })(),
    )
    client = create_queue_redis_client()
    assert isinstance(client, RedisClient)
    assert "upstash" in str(client._redis_url).lower() or "upstash" in client._redis_url


@pytest.mark.unit
def test_dedicated_provider_uses_dedicated_url_when_set(monkeypatch):
    """Dedicated provider uses DEDICATED_REDIS_URL when set."""
    custom_url = "redis://custom-host:6379/1"
    monkeypatch.setattr(
        "src.infra.queue.queue_client_factory.settings",
        type("S", (), {
            "QUEUE_PROVIDER": "dedicated",
            "UPSTASH_REDIS_URL": None,
            "DEDICATED_REDIS_URL": custom_url,
            "REDIS_MAX_CONNECTIONS": 10,
        })(),
    )
    client = create_queue_redis_client()
    assert isinstance(client, RedisClient)
    assert client._redis_url == custom_url


@pytest.mark.unit
def test_dedicated_provider_uses_redis_url_when_dedicated_not_set(monkeypatch):
    """Dedicated provider falls back to redis_url when DEDICATED_REDIS_URL not set."""
    monkeypatch.setattr(
        "src.infra.queue.queue_client_factory.settings",
        type("S", (), {
            "QUEUE_PROVIDER": "dedicated",
            "UPSTASH_REDIS_URL": None,
            "DEDICATED_REDIS_URL": None,
            "REDIS_MAX_CONNECTIONS": 10,
            "redis_url": "redis://localhost:6379/0",
        })(),
    )
    client = create_queue_redis_client()
    assert isinstance(client, RedisClient)
    assert client._redis_url == "redis://localhost:6379/0"


@pytest.mark.unit
def test_invalid_provider_raises(monkeypatch):
    """Invalid QUEUE_PROVIDER raises ValueError."""
    monkeypatch.setattr(
        "src.infra.queue.queue_client_factory.settings",
        type("S", (), {
            "QUEUE_PROVIDER": "invalid",
            "UPSTASH_REDIS_URL": None,
            "DEDICATED_REDIS_URL": None,
            "REDIS_MAX_CONNECTIONS": 10,
        })(),
    )
    with pytest.raises(ValueError, match="Invalid QUEUE_PROVIDER"):
        create_queue_redis_client()
