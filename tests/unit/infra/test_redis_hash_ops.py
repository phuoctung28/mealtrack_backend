# tests/unit/infra/test_redis_hash_ops.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_hset_with_ttl_pipelines_hset_and_expire():
    from src.infra.cache.redis_client import RedisClient
    client = RedisClient.__new__(RedisClient)
    mock_pipe = AsyncMock()
    mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_pipe.__aexit__ = AsyncMock(return_value=False)
    mock_redis = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    client.client = mock_redis

    await client.hset_with_ttl("k", {"a": "1"}, 3600)

    mock_pipe.hset.assert_called_once_with("k", mapping={"a": "1"})
    mock_pipe.expire.assert_called_once_with("k", 3600)
    mock_pipe.execute.assert_called_once()


@pytest.mark.asyncio
async def test_hset_batch_writes_all_items():
    from src.infra.cache.redis_client import RedisClient
    client = RedisClient.__new__(RedisClient)
    mock_pipe = AsyncMock()
    mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_pipe.__aexit__ = AsyncMock(return_value=False)
    mock_redis = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    client.client = mock_redis

    items = [("k1", {"x": "1"}, 100), ("k2", {"y": "2"}, 200)]
    await client.hset_batch(items)

    assert mock_pipe.hset.call_count == 2
    assert mock_pipe.expire.call_count == 2


@pytest.mark.asyncio
async def test_hgetall_batch_returns_list_of_dicts():
    from src.infra.cache.redis_client import RedisClient
    client = RedisClient.__new__(RedisClient)
    mock_pipe = AsyncMock()
    mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_pipe.__aexit__ = AsyncMock(return_value=False)
    mock_pipe.execute = AsyncMock(return_value=[{"a": "1"}, None])
    mock_redis = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    client.client = mock_redis

    results = await client.hgetall_batch(["k1", "k2"])

    assert results == [{"a": "1"}, {}]
