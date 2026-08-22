"""Handler for logging recommended meals through normal meal persistence."""

import logging
from collections.abc import Coroutine
from typing import Any

from src.app.commands.meal_recommendation import LogRecommendedMealCommand
from src.app.events.base import EventHandler, handles
from src.app.services.background_job_scheduler import schedule_background_job
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.app.services.meal_translation_persistence import persist_meal_translation
from src.app.services.recommended_meal_materialization_service import (
    RecommendedMealMaterializationService,
)
from src.domain.model.meal import Meal
from src.domain.model.meal_recommendation import (
    PersistedMealRecommendationSlotMutationResult,
)
from src.domain.services.meal_analysis.meal_translation_service import (
    MealTranslationService,
)

logger = logging.getLogger(__name__)


@handles(LogRecommendedMealCommand)
class LogRecommendedMealCommandHandler(
    EventHandler[
        LogRecommendedMealCommand,
        PersistedMealRecommendationSlotMutationResult,
    ]
):
    def __init__(
        self,
        uow,
        materializer: RecommendedMealMaterializationService | None = None,
        meal_translation_service: MealTranslationService | None = None,
        cache_invalidation: CacheInvalidationService | None = None,
        task_manager=None,
    ):
        self.uow = uow
        self.materializer = materializer or RecommendedMealMaterializationService()
        self.meal_translation_service = meal_translation_service
        self.cache_invalidation = cache_invalidation
        self.task_manager = task_manager

    async def handle(
        self, command: LogRecommendedMealCommand
    ) -> PersistedMealRecommendationSlotMutationResult:
        saved_meal: Meal | None = None
        meal_date = None

        async with self.uow as uow:
            plan, slot, replayed = await uow.meal_recommendation_plans.claim_slot_log(
                user_id=command.user_id,
                plan_id=command.plan_id,
                slot_id=command.slot_id,
                request_id=command.request_id,
            )
            if replayed:
                result = PersistedMealRecommendationSlotMutationResult(
                    plan_id=plan.id,
                    user_id=plan.user_id,
                    slot=slot,
                )
            else:
                meal = await self.materializer.materialize(uow, plan=plan, slot=slot)
                result = await uow.meal_recommendation_plans.finalize_slot_logged(
                    user_id=command.user_id,
                    plan_id=command.plan_id,
                    slot_id=command.slot_id,
                    request_id=command.request_id,
                    meal_id=meal.meal_id,
                )
                saved_meal = meal
                meal_date = slot.slot_date

        # meal_translation uses its own DB session; parent meal must be committed first.
        if saved_meal is not None:
            if self.cache_invalidation is not None and meal_date is not None:
                await self.cache_invalidation.after_meal_write(
                    command.user_id, meal_date
                )
            await self._defer(
                f"recommendation-log-translation:{saved_meal.meal_id}",
                persist_meal_translation(
                    self.meal_translation_service, saved_meal, command.language
                ),
            )

        return result

    async def _defer(self, name: str, coro: Coroutine[Any, Any, Any]) -> None:
        schedule_background_job(self.task_manager, name, coro, logger=logger)
