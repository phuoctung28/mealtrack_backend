import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_skips_if_sentinel_exists():
    """Pre-compute is skipped when sentinel key already exists in Redis."""
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=True)
    svc = DailyContextPrecomputeService(redis_client=redis)

    with patch.object(svc, "_precompute_db_sync") as mock_sync:
        await svc.precompute_for_timezone("Asia/Ho_Chi_Minh", date(2026, 4, 22))
        mock_sync.assert_not_called()


@pytest.mark.asyncio
async def test_runs_and_sets_sentinel_when_missing():
    """Pre-compute runs and sets sentinel when key is absent."""
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=False)
    redis.hset_batch = AsyncMock()
    redis.set = AsyncMock()
    svc = DailyContextPrecomputeService(redis_client=redis)

    with patch.object(svc, "_precompute_db_sync", return_value=[]) as mock_sync:
        await svc.precompute_for_timezone("Asia/Ho_Chi_Minh", date(2026, 4, 22))
        mock_sync.assert_called_once()
        redis.set.assert_called_once()


def test_sentinel_key_format():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    svc = DailyContextPrecomputeService(redis_client=MagicMock())
    key = svc.sentinel_key(date(2026, 4, 22), "Asia/Ho_Chi_Minh")
    assert key == "precomputed:2026-04-22:Asia/Ho_Chi_Minh"


def test_context_key_format():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    svc = DailyContextPrecomputeService(redis_client=MagicMock())
    assert svc.context_key("user-123") == "user_daily_context:user-123"


def test_user_calorie_goal_uses_adjusted_weekly_budget_target():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    uow = MagicMock()
    weekly_budget = MagicMock(
        target_calories=14000,
        target_protein=700,
        target_carbs=1750,
        target_fat=420,
    )
    uow.weekly_budgets.find_by_user_and_week.return_value = weekly_budget
    adjusted = MagicMock()
    adjusted.adjusted.calories = 1800

    svc = DailyContextPrecomputeService(redis_client=MagicMock())
    profile = MagicMock()
    tdee_result = MagicMock()
    tdee_result.bmr = 1600
    tdee_result.macros.calories = 2000
    svc._tdee_service.calculate_tdee = MagicMock(return_value=tdee_result)

    with patch(
        "src.infra.services.daily_context_precompute_service.build_tdee_request",
        return_value=MagicMock(),
    ), patch(
        "src.infra.services.daily_context_precompute_service.WeeklyBudgetService.get_effective_adjusted_daily",
        return_value=adjusted,
    ) as mock_adjusted:
        result = svc._get_user_calorie_goal(
            uow, "user-123", date(2026, 5, 17), profile, "Asia/Ho_Chi_Minh"
        )

    assert result == 1800
    mock_adjusted.assert_called_once()
