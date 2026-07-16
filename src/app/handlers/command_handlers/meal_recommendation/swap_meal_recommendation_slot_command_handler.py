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
                expected_version=command.expected_version,
                alternative_recipe_version_id=command.alternative_recipe_version_id,
                reason=command.reason,
            )
