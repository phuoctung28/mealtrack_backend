"""Integration tests for AsyncWeeklyBudgetRepository."""

import pytest
import uuid
from datetime import date
from src.infra.repositories.weekly_budget_repository_async import (
    AsyncWeeklyBudgetRepository,
)
from src.domain.model.weekly import WeeklyMacroBudget


def _make_budget(user_id: str, week_start: date) -> WeeklyMacroBudget:
    return WeeklyMacroBudget(
        weekly_budget_id=str(uuid.uuid4()),
        user_id=user_id,
        week_start_date=week_start,
        target_calories=2000.0,
        target_protein=150.0,
        target_carbs=200.0,
        target_fat=70.0,
        consumed_calories=0.0,
        consumed_protein=0.0,
        consumed_carbs=0.0,
        consumed_fat=0.0,
    )


@pytest.mark.asyncio
async def test_upsert_then_find(async_db_session):
    user_id = "user-wb-async-01"
    week = date(2026, 4, 13)
    budget = _make_budget(user_id, week)

    repo = AsyncWeeklyBudgetRepository(async_db_session)
    saved = await repo.upsert(budget)

    assert saved.user_id == user_id
    found = await repo.find_by_user_and_week(user_id, week)
    assert found is not None
    assert found.target_calories == 2000.0


@pytest.mark.asyncio
async def test_upsert_updates_targets_on_conflict(async_db_session):
    user_id = "user-wb-async-02"
    week = date(2026, 4, 13)
    budget = _make_budget(user_id, week)

    repo = AsyncWeeklyBudgetRepository(async_db_session)
    await repo.upsert(budget)

    budget.target_calories = 2200.0
    updated = await repo.upsert(budget)
    assert updated.target_calories == 2200.0
