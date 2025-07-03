import logging
from typing import Dict, List, Optional
from datetime import date

from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService
from src.domain.model.meal_plan import PlannedMeal
from src.domain.model.macro_targets import SimpleMacroTargets

logger = logging.getLogger(__name__)


class DailyMealSuggestionHandler:
    """Handler for daily meal suggestion operations"""
    
    def __init__(self, suggestion_service: DailyMealSuggestionService):
        self.suggestion_service = suggestion_service
    
    def get_daily_suggestions(self, user_data: Dict) -> Dict:
        """
        Get daily meal suggestions based on user onboarding data
        
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
            Dictionary with success status and suggested meals
        """
        try:
            logger.info(f"Getting daily meal suggestions for user")
            
            # Validate required fields
            required_fields = ['age', 'gender', 'height', 'weight', 'activity_level', 'goal']
            missing_fields = [field for field in required_fields if field not in user_data]
            
            if missing_fields:
                return {
                    "success": False,
                    "error": "Missing required fields",
                    "message": f"Missing fields: {', '.join(missing_fields)}"
                }
            
            # Generate meal suggestions
            suggested_meals = self.suggestion_service.generate_daily_suggestions(user_data)
            
            # Calculate totals
            total_calories = sum(meal.calories for meal in suggested_meals)
            total_protein = sum(meal.protein for meal in suggested_meals)
            total_carbs = sum(meal.carbs for meal in suggested_meals)
            total_fat = sum(meal.fat for meal in suggested_meals)
            
            # Format response
            return {
                "success": True,
                "date": date.today().isoformat(),
                "meal_count": len(suggested_meals),
                "meals": [meal.to_dict() for meal in suggested_meals],
                "daily_totals": {
                    "calories": round(total_calories, 1),
                    "protein": round(total_protein, 1),
                    "carbs": round(total_carbs, 1),
                    "fat": round(total_fat, 1)
                },
                "target_totals": {
                    "calories": user_data.get('target_calories', 2000),
                    "protein": self._get_macro_value(user_data.get('target_macros'), 'protein', 50),
                    "carbs": self._get_macro_value(user_data.get('target_macros'), 'carbs', 250),
                    "fat": self._get_macro_value(user_data.get('target_macros'), 'fat', 65)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating daily meal suggestions: {str(e)}")
            return {
                "success": False,
                "error": "Failed to generate meal suggestions",
                "message": str(e)
            }
    
    def get_meal_by_type(self, user_data: Dict, meal_type: str) -> Dict:
        """
        Get a single meal suggestion for a specific meal type
        
        Args:
            user_data: User preferences from onboarding
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
        
        Returns:
            Dictionary with success status and suggested meal
        """
        try:
            # Validate meal type
            valid_types = ['breakfast', 'lunch', 'dinner', 'snack']
            if meal_type.lower() not in valid_types:
                return {
                    "success": False,
                    "error": "Invalid meal type",
                    "message": f"Meal type must be one of: {', '.join(valid_types)}"
                }
            
            # Generate all suggestions and filter
            suggested_meals = self.suggestion_service.generate_daily_suggestions(user_data)
            
            # Find the requested meal type
            for meal in suggested_meals:
                if meal.meal_type.value.lower() == meal_type.lower():
                    return {
                        "success": True,
                        "meal": meal.to_dict()
                    }
            
            return {
                "success": False,
                "error": "Meal type not found",
                "message": f"No {meal_type} suggestion was generated"
            }
            
        except Exception as e:
            logger.error(f"Error generating meal suggestion: {str(e)}")
            return {
                "success": False,
                "error": "Failed to generate meal suggestion",
                "message": str(e)
            }
    
    def _get_macro_value(self, target_macros, macro_name: str, default: float) -> float:
        """Helper to get macro value from either MacroTargets object or dict"""
        if not target_macros:
            return default
        
        if isinstance(target_macros, SimpleMacroTargets):
            return getattr(target_macros, macro_name, default)
        elif isinstance(target_macros, dict):
            # For backward compatibility with dict format
            if macro_name == 'protein':
                return target_macros.get('protein_grams', default)
            elif macro_name == 'carbs':
                return target_macros.get('carbs_grams', default)
            elif macro_name == 'fat':
                return target_macros.get('fat_grams', default)
        
        return default