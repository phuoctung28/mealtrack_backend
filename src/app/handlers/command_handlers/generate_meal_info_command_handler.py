"""Handler for GenerateMealInfoCommand."""
import logging

from src.app.commands.meal_info import GenerateMealInfoCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.meal_info import MealInfo
from src.domain.services.meal_info_service import MealInfoService

logger = logging.getLogger(__name__)


@handles(GenerateMealInfoCommand)
class GenerateMealInfoCommandHandler(
    EventHandler[GenerateMealInfoCommand, MealInfo]
):
    """Delegates to MealInfoService to produce meal name, description, and image."""

    def __init__(self, service: MealInfoService):
        self.service = service

    async def handle(self, command: GenerateMealInfoCommand) -> MealInfo:
        return await self.service.generate(
            meal_name=command.meal_name,
            ingredients=command.ingredients,
            meal_type=command.meal_type,
            calories=command.calories,
            protein=command.protein,
            carbs=command.carbs,
            fat=command.fat,
        )
