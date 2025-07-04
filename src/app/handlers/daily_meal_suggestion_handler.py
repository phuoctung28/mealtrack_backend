import logging
from typing import Dict, List, Optional, Tuple
from datetime import date
from dataclasses import dataclass

from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService
from src.domain.model.meal_plan import PlannedMeal
from src.domain.model.macro_targets import SimpleMacroTargets

logger = logging.getLogger(__name__)


@dataclass
class DailyMealSuggestionResult:
    """Result from daily meal suggestion handler."""
    meals: List[PlannedMeal]
    date: str
    daily_totals: SimpleMacroTargets
    daily_calories: float


class DailyMealSuggestionHandler:
    """Handler for daily meal suggestion operations following clean architecture."""
    
    def __init__(self, suggestion_service: DailyMealSuggestionService):
        self.suggestion_service = suggestion_service
    
    def get_daily_suggestions(self, user_data: Dict) -> DailyMealSuggestionResult:
        """
        Get daily meal suggestions based on user onboarding data.
        
        Args:
            user_data: Dictionary containing:
                - age, gender, height, weight
                - activity_level
                - goal
                - dietary_preferences
                - health_conditions
                - target_calories (from macros calculation)
                - target_macros (from macros calculation)
        
        Returns:
            DailyMealSuggestionResult with suggested meals and totals
            
        Raises:
            ValueError: If required fields are missing
            Exception: If suggestion generation fails
        """
        logger.info("Getting daily meal suggestions for user")
        
        # Validate required fields
        required_fields = ['age', 'gender', 'height', 'weight', 'activity_level', 'goal']
        missing_fields = [field for field in required_fields if field not in user_data]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Generate meal suggestions
        suggested_meals = self.suggestion_service.generate_daily_suggestions(user_data)
        
        # Calculate totals
        total_calories = sum(meal.calories for meal in suggested_meals)
        total_protein = sum(meal.protein for meal in suggested_meals)
        total_carbs = sum(meal.carbs for meal in suggested_meals)
        total_fat = sum(meal.fat for meal in suggested_meals)
        
        daily_totals = SimpleMacroTargets(
            protein=round(total_protein, 1),
            carbs=round(total_carbs, 1),
            fat=round(total_fat, 1)
        )
        
        return DailyMealSuggestionResult(
            meals=suggested_meals,
            date=date.today().isoformat(),
            daily_totals=daily_totals,
            daily_calories=round(total_calories, 1)
        )
    
    def get_meal_by_type(self, user_data: Dict, meal_type: str) -> PlannedMeal:
        """
        Get a single meal suggestion for a specific meal type.
        
        Args:
            user_data: User preferences from onboarding
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
        
        Returns:
            PlannedMeal for the requested type
            
        Raises:
            ValueError: If meal type is invalid
            Exception: If no meal of the requested type is found
        """
        # Validate meal type
        valid_types = ['breakfast', 'lunch', 'dinner', 'snack']
        if meal_type.lower() not in valid_types:
            raise ValueError(f"Invalid meal type. Must be one of: {', '.join(valid_types)}")
        
        # Generate all suggestions and filter
        suggested_meals = self.suggestion_service.generate_daily_suggestions(user_data)
        
        # Find the requested meal type
        for meal in suggested_meals:
            if meal.meal_type.value.lower() == meal_type.lower():
                return meal
        
        raise Exception(f"No {meal_type} suggestion was generated")