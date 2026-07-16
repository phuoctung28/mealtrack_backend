from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.model.meal_recommendation import (
    PersistedMealRecommendationAlternative,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)
from src.infra.repositories.meal_recommendation_plan_repository_async import (
    AsyncMealRecommendationPlanRepository,
)


class _Result:
    def __init__(self, one=None):
        self._one = one

    def scalar_one_or_none(self):
        return self._one


class _AsyncSession:
    def __init__(self, results=None):
        self._results = list(results or [])
        self.execute = AsyncMock(side_effect=self._results)
        self.flush = AsyncMock()
        self.added = None
        self.begin_nested = MagicMock(return_value=_NestedTransaction())

    def add(self, row):
        self.added = row


class _NestedTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def _plan() -> PersistedMealRecommendationPlan:
    return PersistedMealRecommendationPlan(
        id="plan-1",
        user_id="user-1",
        status="active",
        timezone="UTC",
        start_date=date(2026, 7, 16),
        daily_calories=2000,
        algorithm_version="catalog_deterministic_v1",
        catalog_release_id="release-1",
        allergy_evaluated=False,
        operation="three_day",
        idempotency_key="key-1",
        request_fingerprint="f" * 64,
        slots=(
            PersistedMealRecommendationSlot(
                id="slot-1",
                slot_date=date(2026, 7, 16),
                day_index=0,
                meal_type="breakfast",
                recipe_version_id="version-1",
                target_calories=500,
                score=1.0,
                position=0,
                alternatives=(
                    PersistedMealRecommendationAlternative(
                        id="alt-1",
                        recipe_version_id="version-2",
                        target_calories=500,
                        score=0.9,
                        position=0,
                    ),
                ),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_save_new_active_plan_supersedes_existing_and_flushes():
    session = _AsyncSession([_Result()])
    repo = AsyncMealRecommendationPlanRepository(session)

    saved = await repo.save_new_active_plan(_plan())

    assert saved.id == "plan-1"
    assert saved.slots[0].alternatives[0].recipe_version_id == "version-2"
    assert session.added is not None
    session.flush.assert_awaited_once()
    session.execute.assert_awaited_once()
    session.begin_nested.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id_scopes_to_owner():
    row = MagicMock()
    row.id = "plan-1"
    row.user_id = "user-1"
    row.status = "active"
    row.timezone = "UTC"
    row.start_date = date(2026, 7, 16)
    row.daily_calories = 2000
    row.algorithm_version = "catalog_deterministic_v1"
    row.catalog_release_id = "release-1"
    row.allergy_evaluated = False
    row.idempotency_key = "key-1"
    row.request_fingerprint = "f" * 64
    row.created_at = None
    row.slots = []
    session = _AsyncSession([_Result(one=row)])
    repo = AsyncMealRecommendationPlanRepository(session)

    result = await repo.get_by_id(user_id="user-1", plan_id="plan-1")

    assert result is not None
    assert result.id == "plan-1"
    statement = str(session.execute.await_args.args[0])
    assert "meal_recommendation_plans.id" in statement
    assert "meal_recommendation_plans.user_id" in statement


@pytest.mark.asyncio
async def test_get_by_idempotency_key_scopes_to_owner_and_operation():
    row = MagicMock()
    row.id = "plan-1"
    row.user_id = "user-1"
    row.status = "active"
    row.timezone = "UTC"
    row.start_date = date(2026, 7, 16)
    row.daily_calories = 2000
    row.algorithm_version = "catalog_deterministic_v1"
    row.catalog_release_id = "release-1"
    row.allergy_evaluated = False
    row.operation = "three_day"
    row.idempotency_key = "key-1"
    row.request_fingerprint = "f" * 64
    row.created_at = None
    row.slots = []
    session = _AsyncSession([_Result(one=row)])
    repo = AsyncMealRecommendationPlanRepository(session)

    result = await repo.get_by_idempotency_key(
        user_id="user-1", operation="three_day", idempotency_key="key-1"
    )

    assert result is not None
    assert result.operation == "three_day"
    statement = str(session.execute.await_args.args[0])
    assert "meal_recommendation_plans.user_id" in statement
    assert "meal_recommendation_plans.operation" in statement
    assert "meal_recommendation_plans.idempotency_key" in statement


@pytest.mark.asyncio
async def test_lock_generation_for_user_uses_transaction_advisory_lock():
    session = _AsyncSession([_Result()])
    repo = AsyncMealRecommendationPlanRepository(session)

    await repo.lock_generation_for_user(user_id="user-1")

    statement = str(session.execute.await_args.args[0])
    assert "pg_advisory_xact_lock" in statement
