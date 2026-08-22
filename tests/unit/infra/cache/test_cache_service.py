"""
Unit tests for CacheService JSON (de)serialization, including the
datetime-with-offset fix that prevented '+HH:MMZ' malformed strings.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.infra.cache.cache_service import CacheService, _json_serializer
from src.infra.event_bus.background_task_manager import BackgroundTaskManager


class _FailingTaskManager:
    def spawn(self, name, coro):
        raise RuntimeError("runner unavailable")

# ---------- Serializer ----------


def test_serializer_naive_datetime_appends_z():
    """Naive datetimes are assumed UTC; legacy 'Z' suffix preserved."""
    dt = datetime(2026, 4, 13, 10, 12, 43)
    assert _json_serializer(dt) == "2026-04-13T10:12:43Z"


def test_serializer_tz_aware_datetime_no_double_z():
    """tz-aware datetimes must NOT get a trailing 'Z' (caused +00:00Z bug)."""
    dt = datetime(2026, 4, 13, 10, 12, 43, 247633, tzinfo=UTC)
    out = _json_serializer(dt)
    assert out == "2026-04-13T10:12:43.247633+00:00"
    assert not out.endswith("Z")


# ---------- Round-trip + legacy heal via get_json ----------


@pytest.fixture
def task_manager():
    return BackgroundTaskManager()


@pytest.fixture
def service(task_manager):
    redis = AsyncMock()
    return CacheService(redis_client=redis, enabled=True, task_manager=task_manager)


@pytest.mark.asyncio
async def test_get_json_heals_legacy_offset_z(service):
    """Legacy entries with '+00:00Z' should be sanitized on read."""
    service.redis.get = AsyncMock(
        return_value='{"updated_at": "2026-04-13T10:12:43.247633+00:00Z"}'
    )
    result = await service.get_json("k")
    assert result == {"updated_at": "2026-04-13T10:12:43.247633+00:00"}


@pytest.mark.asyncio
async def test_get_json_heals_negative_offset_z(service):
    """Sanitizer also fixes negative offsets (e.g. '-05:00Z')."""
    service.redis.get = AsyncMock(return_value='{"t": "2026-04-13T10:12:43-05:00Z"}')
    result = await service.get_json("k")
    assert result == {"t": "2026-04-13T10:12:43-05:00"}


@pytest.mark.asyncio
async def test_get_json_passthrough_when_clean(service):
    """Well-formed payloads pass through unchanged."""
    service.redis.get = AsyncMock(
        return_value='{"updated_at": "2026-04-13T10:12:43.247633+00:00"}'
    )
    result = await service.get_json("k")
    assert result == {"updated_at": "2026-04-13T10:12:43.247633+00:00"}


@pytest.mark.asyncio
async def test_get_json_returns_none_on_miss(service):
    service.redis.get = AsyncMock(return_value=None)
    assert await service.get_json("k") is None


@pytest.mark.asyncio
async def test_get_json_returns_none_on_invalid_json(service):
    service.redis.get = AsyncMock(return_value="not-json")
    assert await service.get_json("k") is None


@pytest.mark.asyncio
async def test_set_json_writes_clean_offset(service):
    """Background cache writes with tz-aware dt produce no '+00:00Z'."""
    service.redis.set = AsyncMock(return_value=True)
    dt = datetime(2026, 4, 13, 10, 12, 43, tzinfo=UTC)
    assert await service.set_json("k", {"updated_at": dt}) is True
    await service._task_manager.drain()
    args, _ = service.redis.set.call_args
    payload = args[1]
    assert "+00:00" in payload
    assert "+00:00Z" not in payload


@pytest.mark.asyncio
async def test_set_json_without_task_manager_does_not_write_redis():
    redis = AsyncMock()
    service = CacheService(redis_client=redis, enabled=True)

    assert await service.set_json("k", {"value": 1}) is False
    redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_json_drops_job_when_runner_rejects_it():
    redis = AsyncMock()
    service = CacheService(
        redis_client=redis,
        enabled=True,
        task_manager=_FailingTaskManager(),
    )

    assert await service.set_json("k", {"value": 1}) is False
    redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalidate_schedules_delete(service, task_manager):
    service.redis.delete = AsyncMock(return_value=True)

    assert await service.invalidate("user:u:daily") is True
    service.redis.delete.assert_not_awaited()

    await task_manager.drain()

    service.redis.delete.assert_awaited_once_with("user:u:daily")


@pytest.mark.asyncio
async def test_invalidate_pattern_schedules_delete_pattern(service, task_manager):
    service.redis.delete_pattern = AsyncMock(return_value=3)

    assert await service.invalidate_pattern("user:u:activities:*") == 0
    service.redis.delete_pattern.assert_not_awaited()

    await task_manager.drain()

    service.redis.delete_pattern.assert_awaited_once_with("user:u:activities:*")
