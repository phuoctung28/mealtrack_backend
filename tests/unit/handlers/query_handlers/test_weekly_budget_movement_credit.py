from datetime import date
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from src.app.handlers.query_handlers.get_weekly_budget_query_handler import (
    GetWeeklyBudgetQueryHandler,
)
from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery
from src.domain.model.weekly import WeeklyMacroBudget
from src.domain.services.weekly_budget_service import (
    AdjustedDailyTargets,
    EffectiveAdjustedResult,
)


@pytest.mark.asyncio
async def test_weekly_budget_response_uses_movement_adjusted_calories():
    week_start = date(2026, 3, 9)
    target_date = week_start
    weekly_budget = WeeklyMacroBudget(
        weekly_budget_id="budget-1",
        user_id="u1",
        week_start_date=week_start,
        target_calories=14000.0,
        target_protein=700.0,
        target_carbs=1750.0,
        target_fat=466.6667,
    )
    effective = EffectiveAdjustedResult(
        adjusted=AdjustedDailyTargets(
            calories=2000.0,
            carbs=250.0,
            fat=66.7,
            protein=100.0,
            bmr_floor_active=False,
            remaining_days=7,
        ),
        consumed_before_today={
            "calories": 0.0,
            "protein": 0.0,
            "carbs": 0.0,
            "fat": 0.0,
        },
        consumed_total={
            "calories": 2100.0,
            "protein": 100.0,
            "carbs": 250.0,
            "fat": 100.0,
        },
        logged_past_days=0,
        skipped_days=0,
        show_logging_prompt=False,
    )

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.weekly_budgets.find_by_user_and_week.return_value = weekly_budget
    mock_uow.weekly_budgets.update = AsyncMock()
    mock_uow.cheat_days.find_by_user_and_date_range.return_value = []

    handler = GetWeeklyBudgetQueryHandler()
    query = GetWeeklyBudgetQuery(
        user_id="u1",
        target_date=target_date,
        header_timezone="UTC",
    )

    with (
        patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler."
            "AsyncUnitOfWork",
            return_value=mock_uow,
        ),
        patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler."
            "resolve_user_timezone_async",
            new_callable=AsyncMock,
            return_value="UTC",
        ),
        patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler."
            "get_zone_info",
            return_value=ZoneInfo("UTC"),
        ),
        patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler."
            "get_user_monday",
            return_value=week_start,
        ),
        patch.object(
            handler,
            "_sync_targets_if_stale",
            AsyncMock(return_value=(weekly_budget, 1600.0)),
        ),
        patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler."
            "WeeklyBudgetService.get_effective_adjusted_daily_async",
            AsyncMock(return_value=effective),
        ),
    ):
        result = await handler.handle(query)

    assert result["consumed_calories"] == 2100.0
    assert result["remaining_calories"] == 11900.0
    assert result["preview_tomorrow_calories"] == pytest.approx(1983.3, abs=1.0)
    assert weekly_budget.consumed_calories == 2100.0
    assert weekly_budget.consumed_protein == 100.0
    assert weekly_budget.consumed_carbs == 250.0
    assert weekly_budget.consumed_fat == 100.0
