from datetime import date
from unittest.mock import AsyncMock

import pytest
from tests.unit.infra.repositories.test_meal_recommendation_plan_repository_async import (
    _plan,
)

from src.app.commands.meal_recommendation import (
    CreateThreeDayMealRecommendationCommand,
    LogRecommendedMealCommand,
)
from src.app.handlers.command_handlers.meal_recommendation.create_three_day_meal_recommendation_command_handler import (
    CreateThreeDayMealRecommendationCommandHandler,
    _request_fingerprint,
)
from src.app.handlers.command_handlers.meal_recommendation.log_recommended_meal_command_handler import (
    LogRecommendedMealCommandHandler,
)
from src.app.handlers.query_handlers.get_meal_recommendation_plan_query_handler import (
    GetMealRecommendationPlanQueryHandler,
)
from src.app.queries.meal_recommendation import GetMealRecommendationPlanQuery
from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationCreationError,
    MealRecommendationPersistenceConflictError,
)
from src.domain.model.meal_recommendation import (
    CatalogRecipeVersion,
    MealRecommendationAlternative,
    MealRecommendationPlan,
    MealRecommendationSlot,
)
from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientAffinityProfile,
)


class _PlanRepo:
    def __init__(self):
        self.existing = None
        self.lock_generation_for_user = AsyncMock()
        self.get_by_idempotency_key = AsyncMock(side_effect=self._get_by_key)
        self.get_by_id = AsyncMock(return_value=_plan())
        self.save_new_active_plan = AsyncMock(side_effect=lambda plan: plan)

    async def _get_by_key(self, **kwargs):
        return self.existing


class _CatalogRepo:
    def __init__(self, release=None, versions=None):
        self.release = release
        self.versions = versions or []

    async def get_active_release(self):
        return self.release

    async def list_active_versions(self):
        return self.versions


class _ConflictPlanRepo(_PlanRepo):
    def __init__(self, replay_plan):
        super().__init__()
        self.existing = replay_plan
        self._reads = 0
        self.save_new_active_plan = AsyncMock(
            side_effect=MealRecommendationPersistenceConflictError
        )

    async def _get_by_key(self, **kwargs):
        self._reads += 1
        return None if self._reads == 1 else self.existing


class _LogPlanRepo(_PlanRepo):
    def __init__(self, *, replayed=False):
        super().__init__()
        self.claim_slot_log = AsyncMock(return_value=(_plan(), _plan().slots[0], replayed))
        self.finalize_slot_logged = AsyncMock(return_value=_plan())


class _Materializer:
    def __init__(self):
        self.materialize = AsyncMock(
            return_value=type("Meal", (), {"meal_id": "meal-1"})()
        )


class _Uow:
    def __init__(self, plans, catalog):
        self.meal_recommendation_plans = plans
        self.catalog_recipes = catalog

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class _Optimizer:
    def build_plan(self, recipes, *, daily_calories, affinity):
        recipe = CatalogRecipeVersion(
            id="version-1",
            recipe_id="recipe-1",
            release_id="release-1",
            recipe_key="recipe-key-1",
            name="Recipe 1",
            cuisine="vietnamese",
            status="published",
            version_number=1,
            calories=500,
            protein_g=20,
            carbs_g=35,
            fat_g=12,
            fiber_g=4,
            meal_types=("breakfast",),
        )
        alternative = CatalogRecipeVersion(
            id="version-2",
            recipe_id="recipe-2",
            release_id="release-1",
            recipe_key="recipe-key-2",
            name="Recipe 2",
            cuisine="vietnamese",
            status="published",
            version_number=1,
            calories=500,
            protein_g=20,
            carbs_g=35,
            fat_g=12,
            fiber_g=4,
            meal_types=("breakfast",),
        )
        return MealRecommendationPlan(
            algorithm_version="catalog_deterministic_v1",
            slots=(
                MealRecommendationSlot(
                    day_index=0,
                    meal_type="breakfast",
                    target_calories=500,
                    recipe=recipe,
                    score=1.0,
                ),
            ),
            alternatives={
                (0, "breakfast"): (
                    MealRecommendationAlternative(
                        day_index=0,
                        meal_type="breakfast",
                        target_calories=500,
                        recipe=alternative,
                        score=0.9,
                    ),
                )
            },
        )


class _HistoryProjector:
    async def build_affinity(self, uow, *, user_id, start_date, timezone):
        return IngredientAffinityProfile(weights={}, confidence=0.0)


def _command() -> CreateThreeDayMealRecommendationCommand:
    return CreateThreeDayMealRecommendationCommand(
        user_id="user-1",
        idempotency_key="key-1",
        start_date=date(2026, 7, 16),
        timezone="UTC",
        daily_calories=2000,
    )


def _log_command() -> LogRecommendedMealCommand:
    return LogRecommendedMealCommand(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="log-1",
    )


@pytest.mark.asyncio
async def test_create_handler_replays_existing_idempotent_plan():
    plans = _PlanRepo()
    plan = _plan()
    plans.existing = plan.__class__(
        **{**plan.__dict__, "request_fingerprint": _request_fingerprint(_command())}
    )
    handler = CreateThreeDayMealRecommendationCommandHandler(
        uow=_Uow(plans, _CatalogRepo()),
        history_projector=_HistoryProjector(),
    )

    result = await handler.handle(_command())

    assert result.id == "plan-1"
    plans.save_new_active_plan.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_handler_conflicts_on_idempotency_fingerprint_mismatch():
    plans = _PlanRepo()
    plans.existing = _plan()
    handler = CreateThreeDayMealRecommendationCommandHandler(
        uow=_Uow(plans, _CatalogRepo()),
        history_projector=_HistoryProjector(),
    )

    with pytest.raises(MealRecommendationCreationError, match="Idempotency-Key"):
        await handler.handle(_command())

    plans.save_new_active_plan.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_handler_fails_closed_without_active_release():
    handler = CreateThreeDayMealRecommendationCommandHandler(
        uow=_Uow(_PlanRepo(), _CatalogRepo(release=None)),
        history_projector=_HistoryProjector(),
    )

    with pytest.raises(MealRecommendationCreationError, match="catalog is unavailable"):
        await handler.handle(_command())


@pytest.mark.asyncio
async def test_create_handler_replays_after_persistence_conflict():
    plan = _plan()
    replay_plan = plan.__class__(
        **{**plan.__dict__, "request_fingerprint": _request_fingerprint(_command())}
    )
    plans = _ConflictPlanRepo(replay_plan)
    handler = CreateThreeDayMealRecommendationCommandHandler(
        uow=_Uow(plans, _CatalogRepo(release=type("Release", (), {"id": "release-1"})())),
        optimizer=_Optimizer(),
        history_projector=_HistoryProjector(),
    )

    result = await handler.handle(_command())

    assert result.id == "plan-1"
    assert plans.get_by_idempotency_key.await_count == 2


@pytest.mark.asyncio
async def test_query_handler_reads_owner_scoped_plan():
    plans = _PlanRepo()
    handler = GetMealRecommendationPlanQueryHandler(
        uow_factory=lambda: _Uow(plans, _CatalogRepo())
    )

    result = await handler.handle(
        GetMealRecommendationPlanQuery(user_id="user-1", plan_id="plan-1")
    )

    assert result is not None
    assert result.id == "plan-1"
    plans.get_by_id.assert_awaited_once_with(user_id="user-1", plan_id="plan-1")


@pytest.mark.asyncio
async def test_log_handler_replays_without_materializing_duplicate_meal():
    plans = _LogPlanRepo(replayed=True)
    materializer = _Materializer()
    handler = LogRecommendedMealCommandHandler(
        uow=_Uow(plans, _CatalogRepo()),
        materializer=materializer,
    )

    result = await handler.handle(_log_command())

    assert result.id == "plan-1"
    plans.claim_slot_log.assert_awaited_once()
    materializer.materialize.assert_not_awaited()
    plans.finalize_slot_logged.assert_not_awaited()


@pytest.mark.asyncio
async def test_log_handler_claims_materializes_then_finalizes():
    plans = _LogPlanRepo(replayed=False)
    materializer = _Materializer()
    handler = LogRecommendedMealCommandHandler(
        uow=_Uow(plans, _CatalogRepo()),
        materializer=materializer,
    )

    result = await handler.handle(_log_command())

    assert result.id == "plan-1"
    plans.claim_slot_log.assert_awaited_once()
    materializer.materialize.assert_awaited_once()
    plans.finalize_slot_logged.assert_awaited_once_with(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="log-1",
        meal_id="meal-1",
    )
