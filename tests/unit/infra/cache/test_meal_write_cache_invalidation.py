from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.meal_write_cache_invalidation import (
    apply_meal_write_cache_invalidation,
)


@pytest.mark.asyncio
async def test_meal_write_invalidation_deletes_daily_macros_key() -> None:
    cache = AsyncMock()
    user_id = "user-1"
    meal_date = date(2026, 9, 11)

    await apply_meal_write_cache_invalidation(cache, user_id, meal_date)

    cache.invalidate.assert_any_await(CacheKeys.daily_macros(user_id, meal_date)[0])
    assert cache.invalidate_pattern.await_count >= 1


@pytest.mark.asyncio
async def test_meal_write_invalidation_covers_moved_meal_dates() -> None:
    cache = AsyncMock()
    user_id = "user-1"

    await apply_meal_write_cache_invalidation(
        cache,
        user_id,
        date(2026, 9, 11),
        old_meal_date=date(2026, 9, 10),
    )

    cache.invalidate.assert_any_await(
        CacheKeys.daily_macros(user_id, date(2026, 9, 11))[0]
    )
    cache.invalidate.assert_any_await(
        CacheKeys.daily_macros(user_id, date(2026, 9, 10))[0]
    )
