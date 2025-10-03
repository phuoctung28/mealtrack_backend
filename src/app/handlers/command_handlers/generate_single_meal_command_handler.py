"""
GenerateSingleMealCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.app.commands.daily_meal import GenerateSingleMealCommand
from src.app.events.base import EventHandler, handles
from src.app.handlers.command_handlers.generate_daily_meal_suggestions_command_handler import \
    GenerateDailyMealSuggestionsCommandHandler
from src.domain.model.macro_targets import SimpleMacroTargets
from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


@handles(GenerateSingleMealCommand)
class GenerateSingleMealCommandHandler(EventHandler[GenerateSingleMealCommand, Dict[str, Any]]):
    """Handler for generating a single meal suggestion."""

    def __init__(self):
        self.suggestion_service = DailyMealSuggestionService()
        self.tdee_service = TdeeCalculationService()

    def set_dependencies(self):
        """No external dependencies needed."""
        pass

    async def handle(self, command: GenerateSingleMealCommand) -> Dict[str, Any]:
        """Generate a single meal suggestion."""
        # Reuse the daily meal handler logic
        daily_handler = GenerateDailyMealSuggestionsCommandHandler()

        # Prepare user data
        user_data = {
            "age": command.age,
            "gender": command.gender,
            "height": command.height,
            "weight": command.weight,
            "activity_level": command.activity_level,
            "goal": command.goal,
            "dietary_preferences": command.dietary_preferences or [],
            "health_conditions": command.health_conditions or [],
        }

        # Calculate TDEE and macros if not provided
        if not command.target_calories or not command.target_macros:
            tdee_result = daily_handler._calculate_tdee_and_macros(command)
            user_data["target_calories"] = tdee_result["target_calories"]
            user_data["target_macros"] = SimpleMacroTargets(**tdee_result["macros"])
        else:
            user_data["target_calories"] = command.target_calories
            user_data["target_macros"] = SimpleMacroTargets(**command.target_macros) if command.target_macros else None

        # Generate suggestions and filter by meal type
        suggested_meals = self.suggestion_service.generate_daily_suggestions(user_data)

        # Find the requested meal type
        for meal in suggested_meals:
            if meal.meal_type.value.lower() == command.meal_type.lower():
                return {
                    "success": True,
                    "meal": daily_handler._format_meal(meal)
                }

        # If not found, generate a specific meal
        # This is a fallback - in reality, the service should handle this
        raise ValueError(f"No {command.meal_type} suggestion was generated")
