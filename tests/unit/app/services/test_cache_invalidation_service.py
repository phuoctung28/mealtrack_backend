"""Tests for after-commit cache-job scheduling and projection coverage."""

from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.domain.cache.cache_keys import CacheKeys


class _FakeTaskManager:
    def __init__(self):
        self.spawned: list[tuple[str, object]] = []

    def spawn(self, name, coro):
        self.spawned.append((name, coro))
        return None


class _FailingTaskManager:
    def spawn(self, name, coro):
        raise RuntimeError("runner unavailable")


@pytest.fixture
def cache_mock():
    mock = AsyncMock()
    mock.invalidate = AsyncMock(return_value=True)
    mock.invalidate_pattern = AsyncMock(return_value=1)
    # CacheInvalidationService prefers the direct background-job methods when
    # the concrete CacheService exposes them. Keep the port mock on its
    # compatibility path for these service-level assertions.
    mock.invalidate_now = None
    mock.invalidate_pattern_now = None
    return mock


@pytest.fixture
def task_manager():
    manager = _FakeTaskManager()
    yield manager
    for _, coro in manager.spawned:
        coro.close()


@pytest.fixture
def service(cache_mock, task_manager):
    return CacheInvalidationService(cache_mock, task_manager=task_manager)


async def _run_job(task_manager, index: int = 0):
    assert len(task_manager.spawned) > index
    await task_manager.spawned[index][1]


@pytest.mark.asyncio
async def test_mutation_seams_enqueue_without_running_redis(
    service, cache_mock, task_manager
):
    await service.after_meal_write("user1", date(2026, 6, 2))

    assert len(task_manager.spawned) == 1
    assert task_manager.spawned[0][0] == "cache:after_meal_write:user1:2026-06-02"
    cache_mock.invalidate.assert_not_awaited()
    cache_mock.invalidate_pattern.assert_not_awaited()


@pytest.mark.asyncio
async def test_after_meal_write_invalidates_all_projections(
    service, cache_mock, task_manager
):
    log_date = date(2026, 6, 2)
    week_start = date(2026, 6, 1)
    await service.after_meal_write("user1", log_date)
    await _run_job(task_manager)

    cache_mock.invalidate_pattern.assert_any_call("user:user1:activities:2026-06-02:*")
    cache_mock.invalidate.assert_any_call(CacheKeys.daily_macros("user1", log_date)[0])
    cache_mock.invalidate.assert_any_call(
        CacheKeys.weekly_budget("user1", week_start)[0]
    )
    cache_mock.invalidate_pattern.assert_any_call(
        CacheKeys.weekly_budget_pattern("user1", week_start)
    )
    cache_mock.invalidate_pattern.assert_any_call("user:user1:nutrition_bulk:*")
    cache_mock.invalidate.assert_any_call(
        CacheKeys.daily_breakdown("user1", week_start)[0]
    )
    cache_mock.invalidate.assert_any_call(CacheKeys.user_streak("user1")[0])


@pytest.mark.asyncio
async def test_after_meal_write_backdated_clears_current_week(
    service, cache_mock, task_manager
):
    current_week_start = date.today() - timedelta(days=date.today().weekday())
    past_week_start = current_week_start - timedelta(days=14)

    await service.after_meal_write("user1", past_week_start)
    await _run_job(task_manager)

    cache_mock.invalidate.assert_any_call(
        CacheKeys.weekly_budget("user1", past_week_start)[0]
    )
    cache_mock.invalidate.assert_any_call(
        CacheKeys.weekly_budget("user1", current_week_start)[0]
    )


@pytest.mark.asyncio
async def test_after_meal_write_retries_transient_redis_failures(
    cache_mock, task_manager
):
    calls: list[str] = []

    def flaky(pattern):
        calls.append(pattern)
        if len(calls) == 1:
            raise ConnectionError("redis down")
        return 1

    cache_mock.invalidate_pattern.side_effect = flaky
    service = CacheInvalidationService(cache_mock, task_manager=task_manager)
    await service.after_meal_write("user1", date(2026, 6, 2))
    await _run_job(task_manager)

    assert calls[0] == calls[1]


@pytest.mark.asyncio
async def test_after_movement_write_enqueues_all_movement_projections(
    service, cache_mock, task_manager
):
    log_date = date(2026, 6, 2)
    week_start = date(2026, 6, 1)
    await service.after_movement_write("user2", log_date)
    await _run_job(task_manager)

    cache_mock.invalidate_pattern.assert_any_call("user:user2:activities:2026-06-02:*")
    cache_mock.invalidate.assert_any_call(CacheKeys.daily_macros("user2", log_date)[0])
    cache_mock.invalidate.assert_any_call(
        CacheKeys.weekly_budget("user2", week_start)[0]
    )
    cache_mock.invalidate_pattern.assert_any_call("user:user2:nutrition_bulk:*")
    cache_mock.invalidate.assert_any_call(
        CacheKeys.daily_breakdown("user2", week_start)[0]
    )


@pytest.mark.asyncio
async def test_after_movement_write_backdated_clears_current_week(
    service, cache_mock, task_manager
):
    current_week_start = date.today() - timedelta(days=date.today().weekday())
    past_date = current_week_start - timedelta(days=14)

    await service.after_movement_write("user2", past_date)
    await _run_job(task_manager)

    cache_mock.invalidate.assert_any_call(
        CacheKeys.weekly_budget("user2", current_week_start)[0]
    )


@pytest.mark.asyncio
async def test_after_hydration_write_enqueues_hydration_and_meal_projections(
    service, cache_mock, task_manager
):
    log_date = date(2026, 6, 2)
    week_start = date(2026, 6, 1)
    await service.after_hydration_write("user3", log_date)
    await _run_job(task_manager)

    cache_mock.invalidate_pattern.assert_any_call("user:user3:activities:2026-06-02:*")
    cache_mock.invalidate_pattern.assert_any_call("user:user3:hydration:2026-06-02:*")
    cache_mock.invalidate.assert_any_call(CacheKeys.daily_macros("user3", log_date)[0])
    cache_mock.invalidate.assert_any_call(
        CacheKeys.weekly_budget("user3", week_start)[0]
    )
    cache_mock.invalidate.assert_any_call(
        CacheKeys.weekly_hydration("user3", week_start)[0]
    )
    cache_mock.invalidate.assert_any_call(
        CacheKeys.daily_breakdown("user3", week_start)[0]
    )
    cache_mock.invalidate.assert_any_call(CacheKeys.user_streak("user3")[0])
    cache_mock.invalidate_pattern.assert_any_call("user:user3:nutrition_bulk:*")


@pytest.mark.asyncio
async def test_after_custom_macros_update_enqueues_target_projections(
    service, cache_mock, task_manager
):
    await service.after_custom_macros_update("user4")
    await _run_job(task_manager)

    cache_mock.invalidate.assert_any_call(CacheKeys.user_tdee("user4")[0])
    cache_mock.invalidate.assert_any_call(CacheKeys.user_profile("user4")[0])
    cache_mock.invalidate_pattern.assert_any_call("user:user4:macros:*")
    cache_mock.invalidate_pattern.assert_any_call("user:user4:nutrition_bulk:*")


@pytest.mark.asyncio
async def test_after_profile_write_covers_all_profile_projections(
    service, cache_mock, task_manager
):
    await service.after_profile_write("user5")
    await _run_job(task_manager)

    cache_mock.invalidate.assert_any_call(CacheKeys.user_profile("user5")[0])
    cache_mock.invalidate.assert_any_call(CacheKeys.user_tdee("user5")[0])
    cache_mock.invalidate.assert_any_call(CacheKeys.user_metrics("user5")[0])
    cache_mock.invalidate_pattern.assert_any_call("user:user5:nutrition_bulk:*")
    cache_mock.invalidate_pattern.assert_any_call("user:user5:daily_breakdown:*")
    cache_mock.invalidate_pattern.assert_any_call(
        CacheKeys.weekly_budget_user_pattern("user5")
    )


@pytest.mark.asyncio
async def test_after_cheat_day_write_invalidates_only_affected_week(
    service, cache_mock, task_manager
):
    cheat_day = date(2026, 6, 3)
    await service.after_cheat_day_write("user6", cheat_day)
    await _run_job(task_manager)

    week_start = date(2026, 6, 1)
    cache_mock.invalidate.assert_any_call(
        CacheKeys.weekly_budget("user6", week_start)[0]
    )
    cache_mock.invalidate_pattern.assert_any_call(
        CacheKeys.weekly_budget_pattern("user6", week_start)
    )


@pytest.mark.asyncio
async def test_after_saved_suggestion_write_invalidates_bookmarks_in_background(
    service, cache_mock, task_manager
):
    await service.after_saved_suggestion_write("user7")
    await _run_job(task_manager)

    cache_mock.invalidate.assert_any_call(CacheKeys.saved_suggestions("user7")[0])


@pytest.mark.asyncio
async def test_no_task_manager_does_not_fallback_to_synchronous_redis(cache_mock):
    service = CacheInvalidationService(cache_mock)
    await service.after_movement_write("user2", date(2026, 6, 2))

    cache_mock.invalidate.assert_not_awaited()
    cache_mock.invalidate_pattern.assert_not_awaited()


@pytest.mark.asyncio
async def test_runner_failure_does_not_escape_committed_business_flow(cache_mock):
    service = CacheInvalidationService(
        cache_mock,
        task_manager=_FailingTaskManager(),
    )

    await service.after_hydration_write("user", date(2026, 6, 2))

    cache_mock.invalidate.assert_not_awaited()
    cache_mock.invalidate_pattern.assert_not_awaited()


@pytest.mark.asyncio
async def test_service_without_cache_is_a_noop():
    service = CacheInvalidationService(None)
    await service.after_meal_write("u", date(2026, 6, 2))
    await service.after_movement_write("u", date(2026, 6, 2))
    await service.after_hydration_write("u", date(2026, 6, 2))
    await service.after_custom_macros_update("u")
