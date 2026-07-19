"""Handler for logging recommended meals through normal meal persistence."""

from src.app.commands.meal_recommendation import LogRecommendedMealCommand
from src.app.events.base import EventHandler, handles
from src.app.services.recommended_meal_materialization_service import (
    RecommendedMealMaterializationService,
)
from src.domain.model.meal_recommendation import PersistedMealRecommendationPlan


@handles(LogRecommendedMealCommand)
class LogRecommendedMealCommandHandler(
    EventHandler[LogRecommendedMealCommand, PersistedMealRecommendationPlan]
):
    def __init__(
        self,
        uow,
        materializer: RecommendedMealMaterializationService | None = None,
    ):
        self.uow = uow
        self.materializer = materializer or RecommendedMealMaterializationService()

    async def handle(
        self, command: LogRecommendedMealCommand
    ) -> PersistedMealRecommendationPlan:
        async with self.uow as uow:
            plan, slot, replayed = await uow.meal_recommendation_plans.claim_slot_log(
                user_id=command.user_id,
                plan_id=command.plan_id,
                slot_id=command.slot_id,
                request_id=command.request_id,
            )
            if replayed:
                return plan
            meal = await self.materializer.materialize(uow, plan=plan, slot=slot)
            return await uow.meal_recommendation_plans.finalize_slot_logged(
                user_id=command.user_id,
                plan_id=command.plan_id,
                slot_id=command.slot_id,
                request_id=command.request_id,
                meal_id=meal.meal_id,
            )
