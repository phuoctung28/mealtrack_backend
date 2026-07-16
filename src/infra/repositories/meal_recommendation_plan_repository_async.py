"""Async repository for durable meal recommendation plans."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationPersistenceConflictError,
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
    MealRecommendationPlanORM,
    MealRecommendationSlotAlternativeORM,
    MealRecommendationSlotORM,
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
