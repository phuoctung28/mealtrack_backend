"""Handler for logging recommended meals through normal meal persistence."""

from __future__ import annotations

import logging

from src.app.commands.meal_recommendation import LogRecommendedMealCommand
from src.app.events.base import EventHandler, handles
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.app.services.meal_value_insight_scheduler import (
    MealInsightEventBus,
    MealInsightTaskScheduler,
    schedule_value_insight_generation,
)
from src.app.services.recommended_meal_materialization_service import (
    RecommendedMealMaterializationService,
)
from src.domain.model.meal import Meal
from src.domain.model.meal_recommendation import (
    PersistedMealRecommendationSlotMutationResult,
)
from src.domain.ports.cache_port import CachePort
from src.domain.ports.meal_insight_ai_port import MealInsightAIPort
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
        meal_value_insight_task_manager: MealInsightTaskScheduler | None = None,
        meal_value_insight_cache: CachePort | None = None,
        meal_value_insight_ai_manager: MealInsightAIPort | None = None,
        meal_value_insight_event_bus: MealInsightEventBus | None = None,
    ):
        self.uow = uow
        self.materializer = materializer or RecommendedMealMaterializationService()
        self.meal_translation_service = meal_translation_service
        self.cache_invalidation = cache_invalidation
        self.meal_value_insight_task_manager = meal_value_insight_task_manager
        self.meal_value_insight_cache = meal_value_insight_cache
        self.meal_value_insight_ai_manager = meal_value_insight_ai_manager
        self.meal_value_insight_event_bus = meal_value_insight_event_bus

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
            await self._persist_request_language_translation(command, saved_meal)
            self._schedule_value_insights(command, saved_meal)

        return result

    def _schedule_value_insights(
        self, command: LogRecommendedMealCommand, meal: Meal
    ) -> None:
        """Best-effort insight warmup; logging still succeeds if scheduling fails."""
        try:
            schedule_value_insight_generation(
                self.meal_value_insight_task_manager,
                meal,
                language=(command.language or "en").strip().lower() or "en",
                cache_service=self.meal_value_insight_cache,
                ai_manager=self.meal_value_insight_ai_manager,
                event_bus=self.meal_value_insight_event_bus,
                user_id=command.user_id,
                source="catalog_log",
            )
        except Exception as exc:
            logger.warning(
                "recommended meal insight schedule failed meal=%s error_type=%s",
                meal.meal_id,
                type(exc).__name__,
            )

    async def _persist_request_language_translation(
        self,
        command: LogRecommendedMealCommand,
        meal: Meal,
    ) -> None:
        """Persist localized meal translation so Today's Meals can show titles."""

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
        except Exception as exc:
            # Logging must succeed even when translation is unavailable.
            logger.warning(
                "recommended meal translation failed meal=%s language=%s error_type=%s",
                meal.meal_id,
                language,
                type(exc).__name__,
            )
