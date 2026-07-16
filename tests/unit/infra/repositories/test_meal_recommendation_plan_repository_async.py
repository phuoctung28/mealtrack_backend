from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationAlreadyLoggedError,
    MealRecommendationIdempotencyConflictError,
    MealRecommendationInvalidAlternativeError,
    MealRecommendationVersionConflictError,
)
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
        self.added_rows = []
        self.begin_nested = MagicMock(return_value=_NestedTransaction())

    def add(self, row):
        self.added = row
        self.added_rows.append(row)


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


class _SlotLogicRepo(AsyncMealRecommendationPlanRepository):
    def __init__(self, slot, *, replay=None, interaction_replay=None, plan_slots=None):
        super().__init__(_AsyncSession())
        self.slot = slot
        self.replay = replay
        self.interaction_replay = interaction_replay
        self.plan_slots = plan_slots or [slot]

    async def _get_swap_replay(self, *, user_id, request_id):
        return self.replay

    async def _get_interaction_replay(
        self, *, user_id, plan_id, slot_id, event_type, request_id
    ):
        return self.interaction_replay

    async def _lock_plan_slot(self, *, user_id, plan_id, slot_id):
        return _plan_row(user_id=user_id, plan_id=plan_id, slots=self.plan_slots), self.slot

    async def _reload_plan(self, plan_row):
        return _plan()

    async def get_by_id(self, *, user_id, plan_id):
        return _plan()


def _slot_row():
    return SimpleNamespace(
        id="slot-1",
        slot_date=date(2026, 7, 16),
        day_index=0,
        meal_type="breakfast",
        version=1,
        recipe_version_id="version-1",
        target_calories=500,
        score=1.0,
        position=0,
        logged_meal_id=None,
        alternatives=[
            SimpleNamespace(
                id="alt-1",
                recipe_version_id="version-2",
                target_calories=520,
                score=0.8,
                position=0,
            )
        ],
    )


def _plan_row(user_id, plan_id, slots):
    return SimpleNamespace(
        id=plan_id,
        user_id=user_id,
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
        created_at=None,
        slots=slots,
    )


def _swap_replay(**overrides):
    data = {
        "plan_id": "plan-1",
        "slot_id": "slot-1",
        "expected_version": 1,
        "requested_recipe_version_id": None,
        "reason": "user_requested",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_swap_slot_updates_selected_slot_and_records_audit_rows():
    slot = _slot_row()
    repo = _SlotLogicRepo(slot)

    result = await repo.swap_slot(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="swap-1",
        expected_version=1,
        alternative_recipe_version_id=None,
        reason="user_requested",
    )

    assert result.id == "plan-1"
    assert slot.recipe_version_id == "version-2"
    assert slot.target_calories == 520
    assert slot.version == 2
    assert len(repo._session.added_rows) == 2
    repo._session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_swap_slot_replays_matching_request_after_lock():
    slot = _slot_row()
    repo = _SlotLogicRepo(slot, replay=_swap_replay())

    result = await repo.swap_slot(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="swap-1",
        expected_version=1,
        alternative_recipe_version_id=None,
        reason="user_requested",
    )

    assert result.id == "plan-1"
    assert slot.recipe_version_id == "version-1"
    repo._session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_swap_slot_conflicts_when_request_id_reused_with_different_payload():
    repo = _SlotLogicRepo(_slot_row(), replay=_swap_replay(reason="alternative_selected"))

    with pytest.raises(MealRecommendationIdempotencyConflictError):
        await repo.swap_slot(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="swap-1",
            expected_version=1,
            alternative_recipe_version_id=None,
            reason="user_requested",
        )


@pytest.mark.asyncio
async def test_swap_slot_rejects_stale_expected_version():
    repo = _SlotLogicRepo(_slot_row())

    with pytest.raises(MealRecommendationVersionConflictError):
        await repo.swap_slot(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="swap-1",
            expected_version=2,
            alternative_recipe_version_id=None,
            reason="user_requested",
        )


@pytest.mark.asyncio
async def test_swap_slot_rejects_invalid_alternative():
    repo = _SlotLogicRepo(_slot_row())

    with pytest.raises(MealRecommendationInvalidAlternativeError):
        await repo.swap_slot(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="swap-1",
            expected_version=1,
            alternative_recipe_version_id="missing-version",
            reason="user_requested",
        )


@pytest.mark.asyncio
async def test_swap_slot_maps_duplicate_request_constraint_to_idempotency_conflict():
    repo = _SlotLogicRepo(_slot_row())
    repo._session.flush.side_effect = IntegrityError(
        "INSERT",
        {},
        Exception("uq_meal_recommendation_swaps_user_request"),
    )

    with pytest.raises(MealRecommendationIdempotencyConflictError):
        await repo.swap_slot(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="swap-1",
            expected_version=1,
            alternative_recipe_version_id=None,
            reason="user_requested",
        )


@pytest.mark.asyncio
async def test_swap_slot_rejects_alternative_already_selected_by_other_slot():
    slot = _slot_row()
    other_slot = _slot_row()
    other_slot.id = "slot-2"
    other_slot.recipe_version_id = "version-2"
    repo = _SlotLogicRepo(slot, plan_slots=[slot, other_slot])

    with pytest.raises(MealRecommendationInvalidAlternativeError):
        await repo.swap_slot(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="swap-1",
            expected_version=1,
            alternative_recipe_version_id="version-2",
            reason="user_requested",
        )


@pytest.mark.asyncio
async def test_claim_slot_log_rejects_second_log():
    slot = _slot_row()
    slot.logged_meal_id = "meal-1"
    repo = _SlotLogicRepo(slot)

    with pytest.raises(MealRecommendationAlreadyLoggedError):
        await repo.claim_slot_log(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="log-2",
        )


@pytest.mark.asyncio
async def test_claim_slot_log_replays_without_new_meal_claim():
    repo = _SlotLogicRepo(_slot_row(), interaction_replay=SimpleNamespace(meal_id="meal-1"))

    plan, slot, replayed = await repo.claim_slot_log(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="log-1",
    )

    assert plan.id == "plan-1"
    assert slot.id == "slot-1"
    assert replayed is True
    repo._session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_finalize_slot_logged_updates_claimed_interaction_and_slot():
    slot = _slot_row()
    interaction = SimpleNamespace(meal_id=None)
    repo = _SlotLogicRepo(slot, interaction_replay=interaction)

    result = await repo.finalize_slot_logged(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="log-1",
        meal_id="meal-1",
    )

    assert result.id == "plan-1"
    assert slot.logged_meal_id == "meal-1"
    assert interaction.meal_id == "meal-1"
    repo._session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_finalize_slot_logged_rejects_different_existing_meal():
    slot = _slot_row()
    slot.logged_meal_id = "meal-1"
    repo = _SlotLogicRepo(slot, interaction_replay=SimpleNamespace(meal_id="meal-1"))

    with pytest.raises(MealRecommendationAlreadyLoggedError):
        await repo.finalize_slot_logged(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="log-1",
            meal_id="meal-2",
        )
