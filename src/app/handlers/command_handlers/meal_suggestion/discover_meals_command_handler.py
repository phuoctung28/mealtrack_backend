"""
Handler for lightweight meal discovery generation.
"""

from typing import List, Tuple

from src.app.commands.meal_suggestion import DiscoverMealsCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.meal_suggestion import SuggestionSession
from src.domain.services.meal_suggestion.suggestion_orchestration_service import (
    SuggestionOrchestrationService,
)


@handles(DiscoverMealsCommand)
class DiscoverMealsCommandHandler(
    EventHandler[DiscoverMealsCommand, Tuple[SuggestionSession, List[dict]]]
):
    """Generate lightweight discovery meal options through the app layer."""

    def __init__(self, service: SuggestionOrchestrationService):
        self.service = service

    async def handle(
        self, command: DiscoverMealsCommand
    ) -> Tuple[SuggestionSession, List[dict]]:
        return await self.service.generate_discovery(
            user_id=command.user_id,
            meal_type=command.meal_type,
            meal_portion_type=command.meal_portion_type,
            ingredients=command.ingredients,
            cooking_time_minutes=command.time_available_minutes,
            session_id=command.session_id,
            language=command.language,
            cuisine_region=command.cuisine_region,
            calorie_target_override=command.calorie_target,
            protein_target=command.protein_target,
            carbs_target=command.carbs_target,
            fat_target=command.fat_target,
            count=command.count,
        )
