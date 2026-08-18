"""Handler for logging another meal from an already logged catalog slot."""

from __future__ import annotations

import logging

from src.app.commands.meal_recommendation import RelogRecommendedMealCommand
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
from src.domain.utils.timezone_utils import user_today

logger = logging.getLogger(__name__)


@handles(RelogRecommendedMealCommand)
class RelogRecommendedMealCommandHandler(
    EventHandler[
        RelogRecommendedMealCommand,
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
        self, command: RelogRecommendedMealCommand
    ) -> PersistedMealRecommendationSlotMutationResult:
        saved_meal: Meal | None = None
        meal_date = None

        async with self.uow as uow:
            plan, slot, replayed, replayed_meal_id = (
                await uow.meal_recommendation_plans.claim_slot_relog(
                    user_id=command.user_id,
                    plan_id=command.plan_id,
                    slot_id=command.slot_id,
                    request_id=command.request_id,
                )
            )
            if replayed:
                result = PersistedMealRecommendationSlotMutationResult(
                    plan_id=plan.id,
                    user_id=plan.user_id,
                    slot=slot,
                    meal_id=replayed_meal_id,
                )
            else:
                meal_date = user_today(plan.timezone)
                meal = await self.materializer.materialize(
                    uow,
                    plan=plan,
                    slot=slot,
                    meal_date=meal_date,
                )
                result = await uow.meal_recommendation_plans.finalize_slot_relogged(
                    user_id=command.user_id,
                    plan_id=command.plan_id,
                    slot_id=command.slot_id,
                    request_id=command.request_id,
                    meal_id=meal.meal_id,
                )
                saved_meal = meal

        if saved_meal is not None:
            if self.cache_invalidation is not None and meal_date is not None:
                await self.cache_invalidation.after_meal_write(
                    command.user_id, meal_date
                )
            await self._persist_request_language_translation(command, saved_meal)
            self._schedule_value_insights(command, saved_meal)

        return result

    def _schedule_value_insights(
        self, command: RelogRecommendedMealCommand, meal: Meal
    ) -> None:
        try:
            schedule_value_insight_generation(
                self.meal_value_insight_task_manager,
                meal,
                language=(command.language or "en").strip().lower() or "en",
                cache_service=self.meal_value_insight_cache,
                ai_manager=self.meal_value_insight_ai_manager,
                event_bus=self.meal_value_insight_event_bus,
                user_id=command.user_id,
                source="catalog_relog",
            )
        except Exception as exc:
            logger.warning(
                "recommended meal relog insight schedule failed meal=%s error_type=%s",
                meal.meal_id,
                type(exc).__name__,
            )

    async def _persist_request_language_translation(
        self,
        command: RelogRecommendedMealCommand,
        meal: Meal,
    ) -> None:
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
            logger.warning(
                "recommended meal relog translation failed meal=%s language=%s error_type=%s",
                meal.meal_id,
                language,
                type(exc).__name__,
            )
