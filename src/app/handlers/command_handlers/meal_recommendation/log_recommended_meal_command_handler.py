"""Handler for logging recommended meals through normal meal persistence."""

from __future__ import annotations

import logging

from src.app.commands.meal_recommendation import LogRecommendedMealCommand
from src.app.events.base import EventHandler, handles
from src.app.services.cache_invalidation_service import CacheInvalidationService
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
    ):
        self.uow = uow
        self.materializer = materializer or RecommendedMealMaterializationService()
        self.meal_translation_service = meal_translation_service
        self.cache_invalidation = cache_invalidation

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
            await self._persist_request_language_translation(command, saved_meal)
            if self.cache_invalidation is not None and meal_date is not None:
                await self.cache_invalidation.after_meal_write(
                    command.user_id, meal_date
                )

        return result

    async def _persist_request_language_translation(
        self,
        command: LogRecommendedMealCommand,
        meal: Meal,
    ) -> None:
        """Persist meal translation so Today's Meals can show localized titles."""

        language = (command.language or "en").strip().lower()
        if language == "en" or self.meal_translation_service is None:
            return

        nutrition = getattr(meal, "nutrition", None)
        food_items = list(getattr(nutrition, "food_items", None) or [])
        dish_name = getattr(meal, "dish_name", None) or ""
        if not dish_name and not food_items:
            return

        try:
            await self.meal_translation_service.translate_meal(
                meal=meal,
                dish_name=dish_name,
                food_items=food_items,
                target_language=language,
            )
            logger.info(
                "recommended meal translated meal=%s language=%s",
                meal.meal_id,
                language,
            )
        except Exception as exc:
            # Logging must succeed even when translation is unavailable.
            logger.warning(
                "recommended meal translation failed meal=%s language=%s error=%s",
                meal.meal_id,
                language,
                exc,
            )
