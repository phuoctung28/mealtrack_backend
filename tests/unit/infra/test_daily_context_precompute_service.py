import pytest
from datetime import date
from types import SimpleNamespace
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


def test_notification_language_prefers_in_app_user_language():
    from src.infra.services.daily_context_precompute_service import (
        _resolve_notification_language,
    )

    assert _resolve_notification_language("en", "vi") == "vi"


def test_notification_language_uses_pref_when_user_language_missing():
    from src.infra.services.daily_context_precompute_service import (
        _resolve_notification_language,
    )

    assert _resolve_notification_language("vi", None) == "vi"


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


def test_reschedule_uses_meal_and_nutrition_for_consumed_calories():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    class Result:
        def __init__(self, one=None, all_=None):
            self._one = one
            self._all = all_ or []

        def fetchone(self):
            return self._one

        def fetchall(self):
            return self._all

    class Session:
        def __init__(self):
            self.queries = []
            self.params = []

        def execute(self, statement, params=None):
            self.queries.append(str(statement))
            self.params.append(params or {})
            index = len(self.queries)
            if index == 1:
                return Result(SimpleNamespace(timezone="Asia/Ho_Chi_Minh"))
            if index == 3:
                return Result(
                    SimpleNamespace(
                        meal_reminders_enabled=False,
                        daily_summary_enabled=False,
                        breakfast_time_minutes=None,
                        lunch_time_minutes=None,
                        dinner_time_minutes=None,
                        daily_summary_time_minutes=None,
                        language="en",
                    )
                )
            if index == 4:
                return Result(all_=[SimpleNamespace(fcm_token="token")])
            if index == 5:
                return Result(SimpleNamespace(gender="male", language_code="en"))
            if index == 6:
                return Result(SimpleNamespace(total=425.0))
            return Result()

    session = Session()
    uow = MagicMock(session=session)
    context = MagicMock()
    context.__enter__.return_value = uow

    svc = DailyContextPrecomputeService(redis_client=MagicMock())
    with patch(
        "src.infra.services.daily_context_precompute_service.UnitOfWork",
        return_value=context,
    ), patch.object(svc, "_get_user_calorie_goal", return_value=2000):
        assert svc._reschedule_user_sync("user-123") == 0

    consumed_query = session.queries[5]
    profile_query = session.queries[4]
    consumed_params = session.params[5]
    assert "up.age" in profile_query
    assert "up.height_cm" in profile_query
    assert "up.weight_kg" in profile_query
    assert "up.fitness_goal" in profile_query
    assert "FROM meal m" in consumed_query
    assert "JOIN nutrition n ON n.meal_id = m.meal_id" in consumed_query
    assert "m.created_at >= :start" in consumed_query
    assert "m.status = 'READY'" in consumed_query
    assert "meal_logs" not in consumed_query
    assert "logged_at" not in consumed_query
    assert consumed_params["start"].tzinfo is None
    assert consumed_params["end"].tzinfo is None
