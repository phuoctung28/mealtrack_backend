import pytest
from datetime import date
from unittest.mock import AsyncMock
from src.app.events.meal.meal_cache_invalidation_required_event import (
    MealCacheInvalidationRequiredEvent,
)
from src.app.handlers.event_handlers.cache_invalidation_event_handler import (
    CacheInvalidationEventHandler,
)
from src.domain.cache.cache_keys import CacheKeys


@pytest.fixture
def cache_mock():
    mock = AsyncMock()
    mock.invalidate = AsyncMock()
    return mock


@pytest.fixture
def handler(cache_mock):
    return CacheInvalidationEventHandler(cache=cache_mock)


@pytest.mark.asyncio
async def test_invalidates_daily_macros(handler, cache_mock):
    event = MealCacheInvalidationRequiredEvent(
        aggregate_id="user-123",
        user_id="user-123",
        meal_date=date(2026, 4, 18),
    )
    await handler.handle(event)
    daily_key, _ = CacheKeys.daily_macros("user-123", date(2026, 4, 18))
    cache_mock.invalidate.assert_any_await(daily_key)


@pytest.mark.asyncio
async def test_invalidates_weekly_budget(handler, cache_mock):
    event = MealCacheInvalidationRequiredEvent(
        aggregate_id="user-123",
        user_id="user-123",
        meal_date=date(2026, 4, 18),
    )
    await handler.handle(event)
    # April 18 2026 is a Saturday; week_start is April 13 (Monday)
    week_start = date(2026, 4, 13)
    weekly_key, _ = CacheKeys.weekly_budget("user-123", week_start)
    cache_mock.invalidate.assert_any_await(weekly_key)


@pytest.mark.asyncio
async def test_invalidates_daily_breakdown(handler, cache_mock):
    event = MealCacheInvalidationRequiredEvent(
        aggregate_id="user-123",
        user_id="user-123",
        meal_date=date(2026, 4, 18),
    )
    await handler.handle(event)
    week_start = date(2026, 4, 13)
    breakdown_key, _ = CacheKeys.daily_breakdown("user-123", week_start)
    cache_mock.invalidate.assert_any_await(breakdown_key)


@pytest.mark.asyncio
async def test_invalidates_streak_and_activities(handler, cache_mock):
    event = MealCacheInvalidationRequiredEvent(
        aggregate_id="user-123",
        user_id="user-123",
        meal_date=date(2026, 4, 18),
    )
    await handler.handle(event)
    streak_key, _ = CacheKeys.user_streak("user-123")
    activities_key, _ = CacheKeys.daily_activities("user-123", date(2026, 4, 18))
    cache_mock.invalidate.assert_any_await(streak_key)
    cache_mock.invalidate.assert_any_await(activities_key)
