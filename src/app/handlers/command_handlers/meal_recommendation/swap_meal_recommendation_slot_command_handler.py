"""Handler for recommendation slot swaps."""

from src.app.commands.meal_recommendation import SwapMealRecommendationSlotCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.meal_recommendation import PersistedMealRecommendationPlan


@handles(SwapMealRecommendationSlotCommand)
class SwapMealRecommendationSlotCommandHandler(
    EventHandler[SwapMealRecommendationSlotCommand, PersistedMealRecommendationPlan]
):
    def __init__(self, uow):
        self.uow = uow

    async def handle(
        self, command: SwapMealRecommendationSlotCommand
    ) -> PersistedMealRecommendationPlan:
        async with self.uow as uow:
            return await uow.meal_recommendation_plans.swap_slot(
                user_id=command.user_id,
                plan_id=command.plan_id,
                slot_id=command.slot_id,
                request_id=command.request_id,
                expected_version=command.expected_selection_version,
                alternative_catalog_meal_id=command.alternative_catalog_meal_id,
                reason=command.reason,
            )
