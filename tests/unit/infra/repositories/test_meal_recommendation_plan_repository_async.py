from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationIdempotencyConflictError,
    MealRecommendationTerminalStateError,
)
from src.domain.model.meal_recommendation import (
    CatalogMeal,
    CatalogMealIngredient,
    MealRecommendationAlternative,
    PersistedMealRecommendationCandidate,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)
from src.infra.repositories.meal_recommendation_plan_repository_async import (
    AsyncMealRecommendationPlanRepository,
    _operation_fingerprint,
)


class _Result:
    def __init__(self, *, one=None, rows=None):
        self._one = one
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def unique(self):
        return self

    def all(self):
        return self._rows


class _AsyncSession:
    def __init__(self, results=None):
        self._results = list(results or [])
        self.execute = AsyncMock(side_effect=self._results)
        self.flush = AsyncMock()
        self.added_rows = []
        self.begin_nested = MagicMock(return_value=_NestedTransaction())

    def add(self, row):
        self.added_rows.append(row)


class _NestedTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def _plan() -> PersistedMealRecommendationPlan:
    selected_meal = _catalog_meal("catalog-1", "Breakfast Rice")
    alternative_meal = _catalog_meal("catalog-2", "Chicken Bowl")
    selected = PersistedMealRecommendationCandidate(
        id="plan-1",
        slot_id="slot-1",
        recommendation_date=date(2026, 7, 16),
        meal_type="breakfast",
        catalog_meal_id=selected_meal.id,
        candidate_rank=0,
        is_selected=True,
        score=Decimal("1.0"),
        selection_version=1,
        catalog_meal=selected_meal,
    )
    alternative = PersistedMealRecommendationCandidate(
        id="alt-1",
        slot_id="slot-1",
        recommendation_date=date(2026, 7, 16),
        meal_type="breakfast",
        catalog_meal_id=alternative_meal.id,
        candidate_rank=1,
        is_selected=False,
        score=Decimal("0.9"),
        selection_version=1,
        catalog_meal=alternative_meal,
    )
    return PersistedMealRecommendationPlan(
        id="plan-1",
        user_id="user-1",
        status="active",
        timezone="UTC",
        start_date=date(2026, 7, 16),
        daily_calories=2000,
        operation="three_day",
        idempotency_key="key-1",
        request_fingerprint="f" * 64,
        slots=(
            PersistedMealRecommendationSlot(
                id="slot-1",
                slot_date=date(2026, 7, 16),
                day_index=0,
                meal_type="breakfast",
                catalog_meal_id="catalog-1",
                target_calories=500,
                score=1.0,
                position=0,
                selected=selected,
                alternatives=(alternative,),
            ),
        ),
    )


def _catalog_meal(catalog_meal_id: str, name: str) -> CatalogMeal:
    return CatalogMeal(
        id=catalog_meal_id,
        catalog_key=f"key-{catalog_meal_id}",
        content_hash=f"{catalog_meal_id:0<64}"[:64],
        name=name,
        cuisine="vietnamese",
        description="Display copy",
        image_url="https://example.com/meal.jpg",
        protein_g=Decimal("25"),
        carbs_g=Decimal("50"),
        fat_g=Decimal("10"),
        fiber_g=Decimal("5"),
        sugar_g=Decimal("4"),
        meal_types=("breakfast",),
        ingredients=(
            CatalogMealIngredient(
                food_reference_id=7,
                display_name="Rice",
                quantity=Decimal("100"),
                unit="g",
            ),
        ),
    )


@pytest.mark.asyncio
async def test_save_new_active_plan_supersedes_existing_and_flushes_candidate_rows():
    session = _AsyncSession([_Result()])
    repo = AsyncMealRecommendationPlanRepository(session)

    saved = await repo.save_new_active_plan(_plan())

    assert saved.id == "plan-1"
    assert len(session.added_rows) == 2
    assert session.added_rows[0].batch_id == "plan-1"
    assert session.added_rows[0].user_id == "user-1"
    assert session.added_rows[1].user_id is None
    session.flush.assert_awaited_once()
    session.begin_nested.assert_called_once()
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_get_by_idempotency_key_reads_anchor_then_batch():
    session = _AsyncSession([_Result(one="plan-1"), _Result(rows=[])])
    repo = AsyncMealRecommendationPlanRepository(session)

    result = await repo.get_by_idempotency_key(
        user_id="user-1", operation="three_day", idempotency_key="key-1"
    )

    assert result is None
    first_statement = str(session.execute.await_args_list[0].args[0])
    assert "meal_recommendations.user_id" in first_statement
    assert "meal_recommendations.operation" in first_statement
    assert "meal_recommendations.idempotency_key" in first_statement


@pytest.mark.asyncio
async def test_lock_generation_for_user_uses_transaction_advisory_lock():
    session = _AsyncSession([_Result()])
    repo = AsyncMealRecommendationPlanRepository(session)

    await repo.lock_generation_for_user(user_id="user-1")

    statement = str(session.execute.await_args.args[0])
    assert "pg_advisory_xact_lock" in statement


@pytest.mark.asyncio
async def test_get_by_id_checks_anchor_owner_not_first_candidate_row():
    rows = _plan_to_candidate_rows(_plan())
    rows = [rows[1], rows[0]]
    session = _AsyncSession([_Result(rows=rows)])
    repo = AsyncMealRecommendationPlanRepository(session)

    result = await repo.get_by_id(user_id="user-1", plan_id="plan-1")

    assert result is not None
    assert result.id == "plan-1"


class _LogReplayRepo(AsyncMealRecommendationPlanRepository):
    def __init__(self, *, replay):
        super().__init__(_AsyncSession())
        self.replay = replay

    async def _get_operation_replay(self, *, user_id, operation_type, request_id):
        return self.replay

    async def _load_slot_for_update(self, *, user_id, batch_id, slot_id):
        rows = _plan_to_candidate_rows(_plan())
        return rows[0], rows


class _SlotMutationRepo(AsyncMealRecommendationPlanRepository):
    def __init__(self, *, replay=None, selected_overrides=None):
        super().__init__(_AsyncSession())
        self.replay = replay
        self.selected_overrides = selected_overrides or {}

    async def _get_operation_replay(self, *, user_id, operation_type, request_id):
        return self.replay

    async def _load_anchor(self, *, user_id, batch_id):
        return _plan_to_candidate_rows(_plan())[0]

    async def _load_slot_for_update(self, *, user_id, batch_id, slot_id):
        rows = _plan_to_candidate_rows(_plan())
        for key, value in self.selected_overrides.items():
            setattr(rows[0], key, value)
        return rows[0], rows

    async def get_slot_detail(self, *, user_id, plan_id, slot_id):
        rows = _plan_to_candidate_rows(_plan())
        for key, value in self.selected_overrides.items():
            setattr(rows[0], key, value)
        return self._rows_to_slot_for_test(rows[0], rows)

    def _rows_to_slot_for_test(self, anchor, rows):
        from src.infra.repositories.meal_recommendation_plan_repository_async import (
            _rows_to_slot_detail,
        )

        return _rows_to_slot_detail(anchor, rows)


class _ConcurrentSkipReplayRepo(_SlotMutationRepo):
    def __init__(self, *, selected_overrides=None):
        super().__init__(selected_overrides=selected_overrides)
        self.replay_calls = 0

    async def _get_operation_replay(self, *, user_id, operation_type, request_id):
        self.replay_calls += 1
        if self.replay_calls == 1:
            return None
        return session_operation(
            operation_type="skip",
            request_id=request_id,
            fingerprint=_operation_fingerprint(plan_id="plan-1", slot_id="slot-1"),
        )


class _OrderedSwapFlushRepo(_SlotMutationRepo):
    def __init__(self):
        super().__init__()
        self.loaded_rows = []

    async def _load_slot_for_update(self, *, user_id, batch_id, slot_id):
        anchor, rows = await super()._load_slot_for_update(
            user_id=user_id,
            batch_id=batch_id,
            slot_id=slot_id,
        )
        self.loaded_rows = rows
        return anchor, rows


@pytest.mark.asyncio
async def test_claim_slot_log_rejects_reused_request_id_for_different_slot():
    repo = _LogReplayRepo(
        replay=SimpleNamespace(batch_id="plan-1", slot_id="other-slot")
    )

    with pytest.raises(MealRecommendationIdempotencyConflictError):
        await repo.claim_slot_log(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="log-1",
        )


@pytest.mark.asyncio
async def test_claim_slot_log_replay_returns_stored_logged_meal_id():
    repo = _LogReplayRepo(
        replay=SimpleNamespace(
            batch_id="plan-1",
            slot_id="slot-1",
            request_fingerprint=_operation_fingerprint(
                plan_id="plan-1",
                slot_id="slot-1",
                meal_id="meal-replayed",
            ),
            result_logged_meal_id="meal-replayed",
        )
    )

    plan, slot, replayed = await repo.claim_slot_log(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="log-1",
    )

    assert replayed is True
    assert slot.logged_meal_id == "meal-replayed"
    assert plan.slots[0].logged_meal_id == "meal-replayed"


@pytest.mark.asyncio
async def test_claim_slot_log_rejects_replay_with_wrong_fingerprint():
    repo = _LogReplayRepo(
        replay=SimpleNamespace(
            batch_id="plan-1",
            slot_id="slot-1",
            request_fingerprint=_operation_fingerprint(
                plan_id="plan-1",
                slot_id="slot-1",
                meal_id="other-meal",
            ),
            result_logged_meal_id="meal-replayed",
        )
    )

    with pytest.raises(MealRecommendationIdempotencyConflictError):
        await repo.claim_slot_log(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="log-1",
        )


@pytest.mark.asyncio
async def test_skip_slot_is_terminal_and_idempotent():
    repo = _SlotMutationRepo()

    first = await repo.skip_slot(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="skip-1",
    )
    replay = _SlotMutationRepo(
        replay=session_operation(
            operation_type="skip",
            request_id="skip-1",
            fingerprint=_operation_fingerprint(plan_id="plan-1", slot_id="slot-1"),
        ),
        selected_overrides={"skipped_at": first.slot.skipped_at},
    )

    replay_result = await replay.skip_slot(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="skip-1",
    )

    assert first.slot.skipped_at is not None
    assert replay_result.slot.skipped_at == first.slot.skipped_at
    with pytest.raises(MealRecommendationTerminalStateError):
        await _SlotMutationRepo(
            selected_overrides={"skipped_at": first.slot.skipped_at}
        ).swap_slot(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="swap-after-skip",
            expected_version=first.slot.selection_version,
            alternative_catalog_meal_id=None,
            reason="user_requested",
        )


@pytest.mark.asyncio
async def test_swap_slot_flushes_deselection_before_selecting_alternative():
    repo = _OrderedSwapFlushRepo()
    flush_states = []

    async def record_flush():
        flush_states.append(
            {
                row.id: row.is_selected
                for row in repo.loaded_rows
                if row.slot_id == "slot-1"
            }
        )

    repo._session.flush.side_effect = record_flush

    result = await repo.swap_slot(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="swap-1",
        expected_version=1,
        alternative_catalog_meal_id=None,
        reason="user_requested",
    )

    assert flush_states[0] == {"plan-1": False, "alt-1": False}
    assert flush_states[-1] == {"plan-1": False, "alt-1": True}
    assert result.slot.catalog_meal_id == "catalog-2"
    assert repo.loaded_rows[0].retired_at is not None
    assert repo.loaded_rows[1].seen_at is not None


@pytest.mark.asyncio
async def test_swap_slot_replenishes_exhausted_pool_and_marks_outcome():
    repo = _SlotMutationRepo()
    rows = _plan_to_candidate_rows(_plan())
    for row in rows:
        row.seen_at = datetime(2026, 7, 16)
    repo._load_slot_for_update = AsyncMock(return_value=(rows[0], rows))  # type: ignore[method-assign]
    fresh = tuple(
        MealRecommendationAlternative(
            day_index=0,
            meal_type="breakfast",
            target_calories=500,
            catalog_meal=_catalog_meal(f"catalog-{index}", f"Fresh {index}"),
            score=0.8,
        )
        for index in range(3, 8)
    )

    result = await repo.swap_slot(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="swap-replenish-1",
        expected_version=1,
        alternative_catalog_meal_id=None,
        reason="user_requested",
        replenishment_alternatives=fresh,
    )

    assert result.outcome == "replenished_candidate"
    assert result.slot.catalog_meal_id == "catalog-3"
    assert len(result.slot.alternatives) == 4
    assert rows[0].retired_at is not None
    assert len(repo._session.added_rows) == 6
    # Domain CatalogMeal must never be assigned onto ORM relationship state.
    for row in repo._session.added_rows:
        if getattr(row, "catalog_meal_id", None) in {
            f"catalog-{index}" for index in range(3, 8)
        }:
            assert not isinstance(getattr(row, "catalog_meal", None), CatalogMeal)


@pytest.mark.asyncio
async def test_skip_slot_rechecks_replay_after_row_lock():
    skipped_at = datetime(2026, 7, 16)
    repo = _ConcurrentSkipReplayRepo(selected_overrides={"skipped_at": skipped_at})

    result = await repo.skip_slot(
        user_id="user-1",
        plan_id="plan-1",
        slot_id="slot-1",
        request_id="skip-1",
    )

    assert repo.replay_calls == 2
    assert result.slot.skipped_at == skipped_at
    assert repo._session.added_rows == []


@pytest.mark.asyncio
async def test_claim_slot_log_rejects_skipped_slot():
    repo = _LogReplayRepo(replay=None)
    repo._load_slot_for_update = AsyncMock(  # type: ignore[method-assign]
        return_value=(
            _plan_to_candidate_rows(_plan())[0],
            [
                SimpleNamespace(
                    **{
                        **row.__dict__,
                        "skipped_at": datetime(2026, 7, 16),
                        "shown_at": None,
                    }
                )
                for row in _plan_to_candidate_rows(_plan())
            ],
        )
    )

    with pytest.raises(MealRecommendationTerminalStateError):
        await repo.claim_slot_log(
            user_id="user-1",
            plan_id="plan-1",
            slot_id="slot-1",
            request_id="log-after-skip",
        )


def _plan_to_candidate_rows(plan):
    rows = []
    for slot in plan.slots:
        candidates = (slot.selected, *slot.alternatives)
        for candidate in candidates:
            rows.append(
                SimpleNamespace(
                    id=candidate.id,
                    batch_id=plan.id,
                    slot_id=slot.id,
                    recommendation_date=slot.slot_date,
                    meal_type=slot.meal_type,
                    catalog_meal_id=candidate.catalog_meal_id,
                    candidate_rank=candidate.candidate_rank,
                    is_selected=candidate.is_selected,
                    score=candidate.score,
                    selection_version=candidate.selection_version,
                    seen_at=candidate.seen_at,
                    retired_at=candidate.retired_at,
                    logged_at=None,
                    logged_meal_id=None,
                    skipped_at=None,
                    shown_at=None,
                    user_id=plan.user_id if candidate.id == plan.id else None,
                    status=plan.status if candidate.id == plan.id else None,
                    timezone=plan.timezone if candidate.id == plan.id else None,
                    start_date=plan.start_date if candidate.id == plan.id else None,
                    target_calories=plan.daily_calories if candidate.id == plan.id else None,
                    operation=plan.operation if candidate.id == plan.id else None,
                    idempotency_key=plan.idempotency_key if candidate.id == plan.id else None,
                    request_fingerprint=plan.request_fingerprint
                    if candidate.id == plan.id
                    else None,
                    created_at=None,
                    catalog_meal=candidate.catalog_meal,
                )
            )
    return rows


def session_operation(*, operation_type, request_id, fingerprint):
    return SimpleNamespace(
        operation_type=operation_type,
        request_id=request_id,
        batch_id="plan-1",
        slot_id="slot-1",
        request_fingerprint=fingerprint,
    )
