import pytest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def clear_sentinel():
    """Wipe in-memory sentinel between tests to prevent leakage."""
    from src.infra.services import daily_context_precompute_service as module
    module._precomputed_today.clear()
    yield
    module._precomputed_today.clear()


@pytest.mark.asyncio
async def test_skips_if_sentinel_in_memory():
    """Pre-compute is skipped when (date, tz) already in _precomputed_today."""
    from src.infra.services import daily_context_precompute_service as module
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    svc = DailyContextPrecomputeService()
    today = date(2026, 4, 22)
    module._precomputed_today.add((today.isoformat(), "Asia/Ho_Chi_Minh"))

    with patch.object(svc, "_precompute_db_sync") as mock_sync:
        await svc.precompute_for_timezone("Asia/Ho_Chi_Minh", today)
        mock_sync.assert_not_called()


@pytest.mark.asyncio
async def test_runs_and_adds_to_sentinel_set():
    """Pre-compute runs and adds (date, tz) to _precomputed_today on success."""
    from src.infra.services import daily_context_precompute_service as module
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    svc = DailyContextPrecomputeService()
    today = date(2026, 4, 22)

    with patch.object(svc, "_precompute_db_sync", return_value=5), \
         patch.object(svc, "_check_db_sentinel", return_value=False):
        await svc.precompute_for_timezone("Asia/Ho_Chi_Minh", today)

    assert (today.isoformat(), "Asia/Ho_Chi_Minh") in module._precomputed_today


@pytest.mark.asyncio
async def test_zero_users_does_not_set_sentinel():
    """When no users are eligible, sentinel must NOT be set (allows retry)."""
    from src.infra.services import daily_context_precompute_service as module
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    svc = DailyContextPrecomputeService()
    today = date(2026, 4, 22)

    with patch.object(svc, "_precompute_db_sync", return_value=0), \
         patch.object(svc, "_check_db_sentinel", return_value=False):
        await svc.precompute_for_timezone("Asia/Ho_Chi_Minh", today)

    assert (today.isoformat(), "Asia/Ho_Chi_Minh") not in module._precomputed_today


@pytest.mark.asyncio
async def test_db_sentinel_fallback_skips_precompute():
    """When in-memory set is empty but DB has notifications, precompute is skipped."""
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    svc = DailyContextPrecomputeService()
    today = date(2026, 4, 22)

    with patch.object(svc, "_check_db_sentinel", return_value=True), \
         patch.object(svc, "_precompute_db_sync") as mock_sync:
        await svc.precompute_for_timezone("Asia/Ho_Chi_Minh", today)
        mock_sync.assert_not_called()


def test_sentinel_key_format():
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    svc = DailyContextPrecomputeService()
    key = svc.sentinel_key(date(2026, 4, 22), "Asia/Ho_Chi_Minh")
    assert key == "precomputed:2026-04-22:Asia/Ho_Chi_Minh"


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

    svc = DailyContextPrecomputeService()

    mock_profile = SimpleNamespace(
        age=30,
        gender="male",
        height_cm=175,
        weight_kg=70,
        body_fat_percentage=None,
        job_type="sedentary",
        training_days_per_week=3,
        training_minutes_per_session=45,
        fitness_goal="maintain",
        training_level="beginner",
    )

    mock_budget = MagicMock()
    mock_budget.target_calories = 14000
    mock_budget.target_protein = 700
    mock_budget.target_carbs = 1750
    mock_budget.target_fat = 350

    mock_uow = MagicMock()
    mock_uow.weekly_budgets.find_by_user_and_week.return_value = mock_budget
    mock_uow.session = MagicMock()

    with patch(
        "src.infra.services.daily_context_precompute_service.WeeklyBudgetService.get_effective_adjusted_daily"
    ) as mock_effective:
        mock_macros = MagicMock()
        mock_macros.calories = 2000.0
        mock_result = MagicMock()
        mock_result.adjusted = mock_macros
        mock_effective.return_value = mock_result

        result = svc._get_user_calorie_goal(
            mock_uow, "user-123", date(2026, 4, 22), mock_profile, "UTC"
        )
        assert result == 2000
