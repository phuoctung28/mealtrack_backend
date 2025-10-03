"""
GenerateDailyMealSuggestionsCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from datetime import date
from typing import Dict, Any
from uuid import uuid4

from src.api.exceptions import ValidationException
from src.app.commands.daily_meal import GenerateDailyMealSuggestionsCommand
from src.app.events.base import EventHandler, handles
from src.app.events.daily_meal import DailyMealsGeneratedEvent
from src.domain.mappers.activity_goal_mapper import ActivityGoalMapper
from src.domain.model.macro_targets import SimpleMacroTargets
from src.domain.model.tdee import TdeeRequest, Sex, UnitSystem
from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


@handles(GenerateDailyMealSuggestionsCommand)
class GenerateDailyMealSuggestionsCommandHandler(EventHandler[GenerateDailyMealSuggestionsCommand, Dict[str, Any]]):
    """Handler for generating daily meal suggestions."""

    def __init__(self, suggestion_service=None, tdee_service=None):
        self.suggestion_service = suggestion_service or DailyMealSuggestionService()
        self.tdee_service = tdee_service or TdeeCalculationService()

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        if 'suggestion_service' in kwargs:
            self.suggestion_service = kwargs['suggestion_service']
        if 'tdee_service' in kwargs:
            self.tdee_service = kwargs['tdee_service']

    async def handle(self, command: GenerateDailyMealSuggestionsCommand) -> Dict[str, Any]:
        """Generate daily meal suggestions based on user preferences."""
        # Validate input
        if command.age < 1 or command.age > 120:
            raise ValidationException("Age must be between 1 and 120")

        if command.height <= 0:
            raise ValidationException("Height must be greater than 0")

        if command.weight <= 0:
            raise ValidationException("Weight must be greater than 0")

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
            tdee_result = self._calculate_tdee_and_macros(command)
            user_data["target_calories"] = tdee_result["target_calories"]
            user_data["target_macros"] = SimpleMacroTargets(**tdee_result["macros"])
        else:
            user_data["target_calories"] = command.target_calories
            user_data["target_macros"] = SimpleMacroTargets(**command.target_macros) if command.target_macros else None

        # Generate meal suggestions
        suggested_meals = self.suggestion_service.generate_daily_suggestions(user_data)

        # Calculate totals
        total_calories = sum(meal.calories for meal in suggested_meals)
        total_protein = sum(meal.protein for meal in suggested_meals)
        total_carbs = sum(meal.carbs for meal in suggested_meals)
        total_fat = sum(meal.fat for meal in suggested_meals)

        # Format meals for response
        meals = []
        meal_ids = []
        for meal in suggested_meals:
            meal_dict = self._format_meal(meal)
            meals.append(meal_dict)
            meal_ids.append(meal.meal_id if hasattr(meal, 'meal_id') else meal.id)

        # Format meals for test compatibility
        suggestions = []
        for meal_dict in meals:
            suggestion = {
                "meal_type": meal_dict["meal_type"],
                "dish_name": meal_dict["name"],
                "calories": meal_dict["calories"],
                "macros": {
                    "protein": meal_dict["protein"],
                    "carbs": meal_dict["carbs"],
                    "fat": meal_dict["fat"]
                }
            }
            suggestions.append(suggestion)

        result = {
            "success": True,
            "date": date.today().isoformat(),
            "meal_count": len(meals),
            "meals": meals,
            "suggestions": suggestions,  # For test compatibility
            "total_calories": round(total_calories, 1),
            "total_macros": {
                "protein": round(total_protein, 1),
                "carbs": round(total_carbs, 1),
                "fat": round(total_fat, 1)
            },
            "daily_totals": {
                "calories": round(total_calories, 1),
                "protein": round(total_protein, 1),
                "carbs": round(total_carbs, 1),
                "fat": round(total_fat, 1)
            },
            "target_totals": {
                "calories": user_data["target_calories"],
                "protein": user_data["target_macros"].protein if user_data["target_macros"] else 0,
                "carbs": user_data["target_macros"].carbs if user_data["target_macros"] else 0,
                "fat": user_data["target_macros"].fat if user_data["target_macros"] else 0
            },
            "events": [
                DailyMealsGeneratedEvent(
                    aggregate_id=str(uuid4()),
                    user_id=str(uuid4()),
                    date=date.today().isoformat(),
                    meal_count=len(meals),
                    total_calories=total_calories,
                    meal_ids=meal_ids
                )
            ]
        }

        return result

    def _calculate_tdee_and_macros(self, command: GenerateDailyMealSuggestionsCommand) -> Dict[str, Any]:
        """Calculate TDEE and macros from command data."""
        # Map to TDEE enums
        sex = Sex.MALE if command.gender.lower() == "male" else Sex.FEMALE

        tdee_request = TdeeRequest(
            age=command.age,
            sex=sex,
            height=command.height,  # height is in cm since unit_system is METRIC
            weight=command.weight,  # weight is in kg since unit_system is METRIC
            activity_level=ActivityGoalMapper.map_activity_level(command.activity_level),
            goal=ActivityGoalMapper.map_goal(command.goal),
            body_fat_pct=None,
            unit_system=UnitSystem.METRIC
        )

        tdee_result = self.tdee_service.calculate_tdee(tdee_request)

        return {
            "target_calories": int(tdee_result.macros.calories),
            "macros": {
                "protein": tdee_result.macros.protein,
                "carbs": tdee_result.macros.carbs,
                "fat": tdee_result.macros.fat
            }
        }

    def _format_meal(self, meal) -> Dict[str, Any]:
        """Format meal for response."""
        # PlannedMeal has prep_time and cook_time attributes directly
        prep_time = meal.prep_time if hasattr(meal, 'prep_time') else 0
        cook_time = meal.cook_time if hasattr(meal, 'cook_time') else 0
        total_time = meal.total_time if hasattr(meal, 'total_time') else prep_time + cook_time

        # PlannedMeal has is_vegetarian, is_vegan, is_gluten_free as boolean attributes
        is_vegetarian = meal.is_vegetarian if hasattr(meal, 'is_vegetarian') else False
        is_vegan = meal.is_vegan if hasattr(meal, 'is_vegan') else False
        is_gluten_free = meal.is_gluten_free if hasattr(meal, 'is_gluten_free') else False

        # Extract cuisine type
        cuisine_type = meal.cuisine_type if hasattr(meal, 'cuisine_type') else None

        return {
            "meal_id": meal.meal_id if hasattr(meal, 'meal_id') else meal.id,
            "meal_type": meal.meal_type.value,
            "name": meal.name,
            "description": meal.description,
            "prep_time": prep_time,
            "cook_time": cook_time,
            "total_time": total_time,
            "calories": int(meal.calories),
            "protein": meal.protein,
            "carbs": meal.carbs,
            "fat": meal.fat,
            "ingredients": meal.ingredients,
            "instructions": meal.instructions if hasattr(meal, 'instructions') else [],
            "is_vegetarian": is_vegetarian,
            "is_vegan": is_vegan,
            "is_gluten_free": is_gluten_free,
            "cuisine_type": cuisine_type
        }
