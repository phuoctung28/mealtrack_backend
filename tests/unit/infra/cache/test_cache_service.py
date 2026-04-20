"""
Unit tests for CacheService JSON (de)serialization, including the
datetime-with-offset fix that prevented '+HH:MMZ' malformed strings.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.infra.cache.cache_service import CacheService, _json_serializer


# ---------- Serializer ----------

def test_serializer_naive_datetime_appends_z():
    """Naive datetimes are assumed UTC; legacy 'Z' suffix preserved."""
    dt = datetime(2026, 4, 13, 10, 12, 43)
    assert _json_serializer(dt) == "2026-04-13T10:12:43Z"


def test_serializer_tz_aware_datetime_no_double_z():
    """tz-aware datetimes must NOT get a trailing 'Z' (caused +00:00Z bug)."""
    dt = datetime(2026, 4, 13, 10, 12, 43, 247633, tzinfo=timezone.utc)
    out = _json_serializer(dt)
    assert out == "2026-04-13T10:12:43.247633+00:00"
    assert not out.endswith("Z")


# ---------- Round-trip + legacy heal via get_json ----------

@pytest.fixture
def service():
    redis = AsyncMock()
    return CacheService(redis_client=redis, enabled=True)


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
    service.redis.get = AsyncMock(
        return_value='{"t": "2026-04-13T10:12:43-05:00Z"}'
    )
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
    """End-to-end: set_json with tz-aware dt produces no '+00:00Z'."""
    service.redis.set = AsyncMock(return_value=True)
    dt = datetime(2026, 4, 13, 10, 12, 43, tzinfo=timezone.utc)
    await service.set_json("k", {"updated_at": dt})
    args, _ = service.redis.set.call_args
    payload = args[1]
    assert "+00:00" in payload
    assert "+00:00Z" not in payload
