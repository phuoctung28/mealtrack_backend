"""
GenerateMealSuggestionsCommandHandler - Handler for generating meal suggestions.
"""
import logging
from typing import Dict, Any

from src.app.commands.meal_suggestion import GenerateMealSuggestionsCommand
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_suggestion_service import MealSuggestionService
from src.infra.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


@handles(GenerateMealSuggestionsCommand)
class GenerateMealSuggestionsCommandHandler(EventHandler[GenerateMealSuggestionsCommand, Dict[str, Any]]):
    """Handler for generating exactly 3 meal suggestions."""
    
    def __init__(self, suggestion_service=None, user_repository=None):
        self.suggestion_service = suggestion_service or MealSuggestionService()
        self.user_repository = user_repository or UserRepository()
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        if 'suggestion_service' in kwargs:
            self.suggestion_service = kwargs['suggestion_service']
        if 'user_repository' in kwargs:
            self.user_repository = kwargs['user_repository']
    
    async def handle(self, command: GenerateMealSuggestionsCommand) -> Dict[str, Any]:
        """
        Generate meal suggestions based on user inputs.
        
        Args:
            command: GenerateMealSuggestionsCommand with user inputs
        
        Returns:
            Dict with request_id, suggestions (list of 3), and generation_token
        """
        try:
            # Determine calorie target
            calorie_target = command.calorie_target
            
            if not calorie_target:
                # Fetch from user profile if not provided
                calorie_target = await self._get_user_calorie_target(command.user_id, command.meal_type)
            
            # Generate suggestions using domain service
            result = self.suggestion_service.generate_suggestions(
                user_id=command.user_id,
                meal_type=command.meal_type,
                calorie_target=calorie_target,
                ingredients=command.ingredients,
                time_available_minutes=command.time_available_minutes,
                dietary_preferences=command.dietary_preferences,
                exclude_ids=command.exclude_ids
            )
            
            logger.info(
                f"Generated {len(result['suggestions'])} meal suggestions for user {command.user_id}, "
                f"meal_type: {command.meal_type}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in GenerateMealSuggestionsCommandHandler: {str(e)}")
            raise
    
    async def _get_user_calorie_target(self, user_id: str, meal_type: str) -> int:
        """
        Get calorie target for a meal from user profile.
        
        Args:
            user_id: User identifier
            meal_type: Type of meal
        
        Returns:
            Calorie target for the meal
        """
        try:
            # Fetch user profile
            user = self.user_repository.find_by_id(user_id)
            
            if user and user.target_calories:
                daily_calories = user.target_calories
            else:
                # Default to 2000 calories per day if not found
                daily_calories = 2000
                logger.warning(f"User {user_id} has no target_calories, using default: {daily_calories}")
            
            # Distribute calories by meal type
            meal_percentages = {
                "breakfast": 0.25,  # 25%
                "lunch": 0.35,      # 35%
                "dinner": 0.30,     # 30%
                "snack": 0.10       # 10%
            }
            
            percentage = meal_percentages.get(meal_type, 0.30)
            meal_calories = int(daily_calories * percentage)
            
            logger.info(f"Calculated calorie target for {meal_type}: {meal_calories} (from daily: {daily_calories})")
            
            return meal_calories
            
        except Exception as e:
            logger.error(f"Error fetching user calorie target: {str(e)}")
            # Return reasonable defaults by meal type
            defaults = {
                "breakfast": 500,
                "lunch": 700,
                "dinner": 600,
                "snack": 200
            }
            return defaults.get(meal_type, 500)

