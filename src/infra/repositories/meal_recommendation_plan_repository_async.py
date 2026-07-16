"""Async repository for durable meal recommendation plans."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationAlreadyLoggedError,
    MealRecommendationIdempotencyConflictError,
    MealRecommendationInvalidAlternativeError,
    MealRecommendationNotFoundError,
    MealRecommendationPersistenceConflictError,
    MealRecommendationVersionConflictError,
)
from src.domain.model.meal_recommendation import (
    PersistedMealRecommendationAlternative,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)
from src.domain.ports.meal_recommendation_plan_repository_port import (
    MealRecommendationPlanRepositoryPort,
)
from src.infra.database.models.meal_recommendation import (
    MealRecommendationInteractionORM,
    MealRecommendationPlanORM,
    MealRecommendationSlotAlternativeORM,
    MealRecommendationSlotORM,
    MealRecommendationSwapORM,
)

_PLAN_LOAD_OPTIONS = (
    selectinload(MealRecommendationPlanORM.slots).selectinload(
        MealRecommendationSlotORM.alternatives
    ),
)


class AsyncMealRecommendationPlanRepository(MealRecommendationPlanRepositoryPort):
    """Repository for owner-scoped durable recommendation aggregates."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(
        self,
        *,
        user_id: str,
        plan_id: str,
    ) -> PersistedMealRecommendationPlan | None:
        result = await self._session.execute(
            select(MealRecommendationPlanORM)
            .where(MealRecommendationPlanORM.id == plan_id)
            .where(MealRecommendationPlanORM.user_id == user_id)
            .options(*_PLAN_LOAD_OPTIONS)
        )
        row = result.scalar_one_or_none()
        return _plan_to_domain(row) if row else None

    async def get_by_idempotency_key(
        self,
        *,
        user_id: str,
        operation: str,
        idempotency_key: str,
    ) -> PersistedMealRecommendationPlan | None:
        result = await self._session.execute(
            select(MealRecommendationPlanORM)
            .where(MealRecommendationPlanORM.user_id == user_id)
            .where(MealRecommendationPlanORM.operation == operation)
            .where(MealRecommendationPlanORM.idempotency_key == idempotency_key)
            .options(*_PLAN_LOAD_OPTIONS)
        )
        row = result.scalar_one_or_none()
        return _plan_to_domain(row) if row else None

    async def lock_generation_for_user(self, *, user_id: str) -> None:
        await self._session.execute(
            select(
                func.pg_advisory_xact_lock(
                    func.hashtext(f"meal_recommendation_plan:{user_id}")
                )
            )
        )

    async def save_new_active_plan(
        self,
        plan: PersistedMealRecommendationPlan,
    ) -> PersistedMealRecommendationPlan:
        row = _plan_to_orm(plan)
        try:
            async with self._session.begin_nested():
                await self._session.execute(
                    update(MealRecommendationPlanORM)
                    .where(MealRecommendationPlanORM.user_id == plan.user_id)
                    .where(MealRecommendationPlanORM.status == "active")
                    .values(status="superseded", superseded_at=datetime.now(UTC))
                )
                self._session.add(row)
                await self._session.flush()
        except IntegrityError as exc:
            raise MealRecommendationPersistenceConflictError from exc
        return _plan_to_domain(row)

    async def swap_slot(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
        expected_version: int,
        alternative_recipe_version_id: str | None,
        reason: str,
    ) -> PersistedMealRecommendationPlan:
        replay = await self._get_swap_replay(user_id=user_id, request_id=request_id)
        if replay is not None:
            return await self._validated_swap_replay(
                replay,
                user_id=user_id,
                plan_id=plan_id,
                slot_id=slot_id,
                expected_version=expected_version,
                alternative_recipe_version_id=alternative_recipe_version_id,
                reason=reason,
            )

        plan_row, slot = await self._lock_plan_slot(
            user_id=user_id,
            plan_id=plan_id,
            slot_id=slot_id,
        )
        replay = await self._get_swap_replay(user_id=user_id, request_id=request_id)
        if replay is not None:
            return await self._validated_swap_replay(
                replay,
                user_id=user_id,
                plan_id=plan_id,
                slot_id=slot_id,
                expected_version=expected_version,
                alternative_recipe_version_id=alternative_recipe_version_id,
                reason=reason,
            )
        if int(slot.version) != expected_version:
            raise MealRecommendationVersionConflictError

        alternatives = sorted(slot.alternatives, key=lambda item: item.position)
        if alternative_recipe_version_id is None:
            target = next(
                (
                    item
                    for item in alternatives
                    if item.recipe_version_id != slot.recipe_version_id
                ),
                None,
            )
        else:
            target = next(
                (
                    item
                    for item in alternatives
                    if item.recipe_version_id == alternative_recipe_version_id
                ),
                None,
            )
        if target is None or target.recipe_version_id == slot.recipe_version_id:
            raise MealRecommendationInvalidAlternativeError
        if _plan_has_recipe_version(
            plan_row,
            slot_id=slot_id,
            recipe_version_id=target.recipe_version_id,
        ):
            raise MealRecommendationInvalidAlternativeError

        from_recipe_version_id = cast(str, slot.recipe_version_id)
        slot.recipe_version_id = target.recipe_version_id
        slot.target_calories = target.target_calories
        slot.score = target.score
        slot.version = int(cast(int, slot.version)) + 1  # type: ignore[assignment]
        self._session.add(
            MealRecommendationSwapORM(
                user_id=user_id,
                plan_id=plan_id,
                slot_id=slot_id,
                request_id=request_id,
                expected_version=expected_version,
                requested_recipe_version_id=alternative_recipe_version_id,
                from_recipe_version_id=from_recipe_version_id,
                to_recipe_version_id=target.recipe_version_id,
                reason=reason,
            )
        )
        self._session.add(
            MealRecommendationInteractionORM(
                user_id=user_id,
                plan_id=plan_id,
                slot_id=slot_id,
                event_type="swap_selected",
                request_id=request_id,
                recipe_version_id=target.recipe_version_id,
                event_metadata={"from_recipe_version_id": from_recipe_version_id},
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            _raise_swap_integrity_error(exc)
        return await self._reload_plan(plan_row)

    async def claim_slot_log(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
    ) -> tuple[PersistedMealRecommendationPlan, PersistedMealRecommendationSlot, bool]:
        plan_row, slot = await self._lock_plan_slot(
            user_id=user_id,
            plan_id=plan_id,
            slot_id=slot_id,
        )
        replay = await self._get_interaction_replay(
            user_id=user_id,
            plan_id=plan_id,
            slot_id=slot_id,
            event_type="meal_logged",
            request_id=request_id,
        )
        if replay is not None:
            return await self._reload_plan(plan_row), _slot_to_domain(slot), True

        if slot.logged_meal_id:
            raise MealRecommendationAlreadyLoggedError

        self._session.add(
            MealRecommendationInteractionORM(
                user_id=user_id,
                plan_id=plan_id,
                slot_id=slot_id,
                event_type="meal_logged",
                request_id=request_id,
                recipe_version_id=slot.recipe_version_id,
                event_metadata={},
            )
        )
        await self._session.flush()
        return _plan_to_domain(plan_row), _slot_to_domain(slot), False

    async def finalize_slot_logged(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
        meal_id: str,
    ) -> PersistedMealRecommendationPlan:
        plan_row, slot = await self._lock_plan_slot(
            user_id=user_id,
            plan_id=plan_id,
            slot_id=slot_id,
        )
        replay = await self._get_interaction_replay(
            user_id=user_id,
            plan_id=plan_id,
            slot_id=slot_id,
            event_type="meal_logged",
            request_id=request_id,
        )
        if replay is None:
            raise MealRecommendationNotFoundError
        if slot.logged_meal_id:
            if cast(str | None, slot.logged_meal_id) == meal_id:
                return await self._reload_plan(plan_row)
            raise MealRecommendationAlreadyLoggedError

        slot.logged_meal_id = meal_id  # type: ignore[assignment]
        slot.logged_at = datetime.now(UTC)  # type: ignore[assignment]
        replay.meal_id = meal_id  # type: ignore[assignment]
        await self._session.flush()
        return await self._reload_plan(plan_row)

    async def _validated_swap_replay(
        self,
        replay: MealRecommendationSwapORM,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        expected_version: int,
        alternative_recipe_version_id: str | None,
        reason: str,
    ) -> PersistedMealRecommendationPlan:
        if (
            cast(str, replay.plan_id) != plan_id
            or cast(str, replay.slot_id) != slot_id
            or cast(int, replay.expected_version) != expected_version
            or cast(str | None, replay.requested_recipe_version_id)
            != alternative_recipe_version_id
            or cast(str, replay.reason) != reason
        ):
            raise MealRecommendationIdempotencyConflictError
        plan = await self.get_by_id(user_id=user_id, plan_id=plan_id)
        if plan is None:
            raise MealRecommendationNotFoundError
        return plan

    async def _get_swap_replay(
        self,
        *,
        user_id: str,
        request_id: str,
    ) -> MealRecommendationSwapORM | None:
        result = await self._session.execute(
            select(MealRecommendationSwapORM)
            .where(MealRecommendationSwapORM.user_id == user_id)
            .where(MealRecommendationSwapORM.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def _get_interaction_replay(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        event_type: str,
        request_id: str,
    ) -> MealRecommendationInteractionORM | None:
        result = await self._session.execute(
            select(MealRecommendationInteractionORM)
            .where(MealRecommendationInteractionORM.user_id == user_id)
            .where(MealRecommendationInteractionORM.plan_id == plan_id)
            .where(MealRecommendationInteractionORM.slot_id == slot_id)
            .where(MealRecommendationInteractionORM.event_type == event_type)
            .where(MealRecommendationInteractionORM.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def _lock_plan_slot(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
    ) -> tuple[MealRecommendationPlanORM, MealRecommendationSlotORM]:
        result = await self._session.execute(
            select(MealRecommendationPlanORM, MealRecommendationSlotORM)
            .join(
                MealRecommendationSlotORM,
                MealRecommendationSlotORM.plan_id == MealRecommendationPlanORM.id,
            )
            .where(MealRecommendationPlanORM.id == plan_id)
            .where(MealRecommendationPlanORM.user_id == user_id)
            .where(MealRecommendationSlotORM.id == slot_id)
            .options(*_PLAN_LOAD_OPTIONS)
            .with_for_update()
        )
        row = result.first()
        if row is None:
            raise MealRecommendationNotFoundError
        return row[0], row[1]

    async def _reload_plan(
        self, plan_row: MealRecommendationPlanORM
    ) -> PersistedMealRecommendationPlan:
        plan = await self.get_by_id(
            user_id=cast(str, plan_row.user_id),
            plan_id=cast(str, plan_row.id),
        )
        if plan is None:
            raise MealRecommendationNotFoundError
        return plan


def _plan_to_orm(plan: PersistedMealRecommendationPlan) -> MealRecommendationPlanORM:
    row = MealRecommendationPlanORM(
        id=plan.id,
        user_id=plan.user_id,
        status=plan.status,
        timezone=plan.timezone,
        start_date=plan.start_date,
        daily_calories=plan.daily_calories,
        algorithm_version=plan.algorithm_version,
        catalog_release_id=plan.catalog_release_id,
        allergy_evaluated=plan.allergy_evaluated,
        operation=plan.operation,
        idempotency_key=plan.idempotency_key,
        request_fingerprint=plan.request_fingerprint,
    )
    row.slots = [
        MealRecommendationSlotORM(
            id=slot.id,
            slot_date=slot.slot_date,
            day_index=slot.day_index,
            meal_type=slot.meal_type,
            recipe_version_id=slot.recipe_version_id,
            target_calories=slot.target_calories,
            score=slot.score,
            position=slot.position,
            version=slot.version,
            logged_meal_id=slot.logged_meal_id,
            alternatives=[
                MealRecommendationSlotAlternativeORM(
                    id=alternative.id,
                    recipe_version_id=alternative.recipe_version_id,
                    target_calories=alternative.target_calories,
                    score=alternative.score,
                    position=alternative.position,
                )
                for alternative in slot.alternatives
            ],
        )
        for slot in plan.slots
    ]
    return row


def _plan_has_recipe_version(
    plan_row: MealRecommendationPlanORM,
    *,
    slot_id: str,
    recipe_version_id: str,
) -> bool:
    return any(
        cast(str, other_slot.id) != slot_id
        and cast(str, other_slot.recipe_version_id) == recipe_version_id
        for other_slot in getattr(plan_row, "slots", ())
    )


def _raise_swap_integrity_error(exc: IntegrityError) -> None:
    detail = f"{exc.orig!s} {exc!s}"
    if "uq_meal_recommendation_swaps_user_request" in detail:
        raise MealRecommendationIdempotencyConflictError from exc
    raise MealRecommendationInvalidAlternativeError from exc


def _plan_to_domain(
    row: MealRecommendationPlanORM,
) -> PersistedMealRecommendationPlan:
    return PersistedMealRecommendationPlan(
        id=cast(str, row.id),
        user_id=cast(str, row.user_id),
        status=cast(str, row.status),
        timezone=cast(str, row.timezone),
        start_date=cast(date, row.start_date),
        daily_calories=cast(int, row.daily_calories),
        algorithm_version=cast(str, row.algorithm_version),
        catalog_release_id=cast(str, row.catalog_release_id),
        allergy_evaluated=cast(bool, row.allergy_evaluated),
        operation=cast(str, row.operation),
        idempotency_key=cast(str, row.idempotency_key),
        request_fingerprint=cast(str, row.request_fingerprint),
        created_at=cast(datetime | None, row.created_at),
        slots=tuple(_slot_to_domain(slot) for slot in row.slots),
    )


def _slot_to_domain(
    row: MealRecommendationSlotORM,
) -> PersistedMealRecommendationSlot:
    return PersistedMealRecommendationSlot(
        id=cast(str, row.id),
        slot_date=cast(date, row.slot_date),
        day_index=cast(int, row.day_index),
        meal_type=cast(str, row.meal_type),
        recipe_version_id=cast(str, row.recipe_version_id),
        target_calories=cast(int, row.target_calories),
        score=cast(float, row.score),
        position=cast(int, row.position),
        version=cast(int, row.version),
        logged_meal_id=cast(str | None, row.logged_meal_id),
        alternatives=tuple(
            _alternative_to_domain(alternative) for alternative in row.alternatives
        ),
    )


def _alternative_to_domain(
    row: MealRecommendationSlotAlternativeORM,
) -> PersistedMealRecommendationAlternative:
    return PersistedMealRecommendationAlternative(
        id=cast(str, row.id),
        recipe_version_id=cast(str, row.recipe_version_id),
        target_calories=cast(int, row.target_calories),
        score=cast(float, row.score),
        position=cast(int, row.position),
    )
