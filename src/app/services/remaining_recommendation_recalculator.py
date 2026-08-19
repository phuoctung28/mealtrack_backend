"""Re-select remaining Home slots after a catalog meal is logged."""

from __future__ import annotations

import logging
from datetime import date

from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationCreationError,
)
from src.domain.services.meal_recommendation.calorie_allocation_policy import (
    CalorieAllocationPolicy,
)
from src.domain.services.meal_recommendation.three_day_plan_optimizer import (
    ThreeDayPlanOptimizer,
)

logger = logging.getLogger(__name__)


class RemainingRecommendationRecalculator:
    """Swap leftover unlogged slots that still recommend a just-logged meal."""

    def __init__(
        self,
        uow_factory,
        *,
        optimizer: ThreeDayPlanOptimizer | None = None,
        snapshot_service=None,
        history_projector=None,
        allocation: CalorieAllocationPolicy | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._optimizer = optimizer or ThreeDayPlanOptimizer()
        self._snapshot_service = snapshot_service
        self._history_projector = history_projector
        self._allocation = allocation or CalorieAllocationPolicy()

    async def recalculate(
        self,
        *,
        user_id: str,
        meal_date: date,
        logged_catalog_meal_id: str,
        logged_slot_id: str | None,
        request_id: str,
    ) -> None:
        try:
            async with self._uow_factory() as uow:
                plan_id = await uow.meal_recommendation_plans.find_active_plan_id(
                    user_id=user_id
                )
                if plan_id is None:
                    return
                plan = await uow.meal_recommendation_plans.get_by_id(
                    user_id=user_id,
                    plan_id=plan_id,
                )
                if plan is None:
                    return
                remaining = [
                    slot
                    for slot in plan.slots
                    if slot.slot_date == meal_date
                    and slot.logged_meal_id is None
                    and slot.skipped_at is None
                    and slot.id != logged_slot_id
                ]
                duplicates = [
                    slot
                    for slot in remaining
                    if slot.catalog_meal_id == logged_catalog_meal_id
                ]
                for index, slot in enumerate(duplicates):
                    await self._swap_duplicate(
                        uow,
                        user_id=user_id,
                        plan_id=plan.id,
                        slot=slot,
                        request_id=f"{request_id}:recalc:{index}",
                    )
        except MealRecommendationCreationError:
            logger.info(
                "recommendation_recalc_skipped user_id=%s date=%s",
                user_id,
                meal_date,
            )
        except Exception:
            logger.warning(
                "recommendation_recalc_failed user_id=%s date=%s",
                user_id,
                meal_date,
                exc_info=True,
            )

    async def _swap_duplicate(self, uow, *, user_id, plan_id, slot, request_id) -> None:
        replenishment = ()
        context_loader = getattr(
            uow.meal_recommendation_plans,
            "get_slot_replenishment_context",
            None,
        )
        if (
            context_loader
            and self._snapshot_service is not None
            and self._history_projector is not None
        ):
            context = await context_loader(
                user_id=user_id,
                plan_id=plan_id,
                slot_id=slot.id,
            )
            if context is not None:
                current, seen_ids, other_selected_ids, timezone = context
                snapshot = await self._snapshot_service.get_snapshot(uow)
                affinity = await self._history_projector.build_affinity(
                    uow,
                    user_id=user_id,
                    start_date=current.slot_date,
                    timezone=timezone,
                )
                excluded_ids = set(seen_ids) | set(other_selected_ids)
                excluded_ids.add(current.catalog_meal_id)
                result = self._optimizer.select_slot_replenishment(
                    list(snapshot.meals),
                    meal_type=current.meal_type,
                    target_calories=current.target_calories,
                    excluded_catalog_meal_ids=excluded_ids,
                    affinity=affinity,
                    ingredient_statistics=snapshot.ingredient_statistics,
                )
                if not hasattr(result, "message"):
                    replenishment = result
        if not replenishment and not getattr(slot, "alternatives", ()):
            return
        await uow.meal_recommendation_plans.swap_slot(
            user_id=user_id,
            plan_id=plan_id,
            slot_id=slot.id,
            request_id=request_id,
            expected_version=slot.selection_version,
            alternative_catalog_meal_id=None,
            reason="catalog_log_recalculate",
            replenishment_alternatives=replenishment,
        )
