"""
Command handlers for daily meal domain - write operations.
"""
import logging
from datetime import date
from typing import Dict, Any

from src.app.commands.daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    GenerateSingleMealCommand
)
from src.app.events.base import EventHandler, handles
from src.app.events.daily_meal import (
    DailyMealsGeneratedEvent
)
from src.domain.model.macro_targets import SimpleMacroTargets
from src.domain.model.tdee import TdeeRequest, Sex, ActivityLevel, Goal, UnitSystem
from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


@handles(GenerateDailyMealSuggestionsCommand)
class GenerateDailyMealSuggestionsCommandHandler(EventHandler[GenerateDailyMealSuggestionsCommand, Dict[str, Any]]):
    """Handler for generating daily meal suggestions."""
    
    def __init__(self):
        self.suggestion_service = DailyMealSuggestionService()
        self.tdee_service = TdeeCalculationService()
    
    def set_dependencies(self):
        """No external dependencies needed."""
        pass
    
    async def handle(self, command: GenerateDailyMealSuggestionsCommand) -> Dict[str, Any]:
        """Generate daily meal suggestions based on user preferences."""
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
            user_data["target_macros"] = tdee_result["macros"]
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
            meal_ids.append(meal.id)
        
        result = {
            "success": True,
            "date": date.today().isoformat(),
            "meal_count": len(meals),
            "meals": meals,
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
                    aggregate_id=command.correlation_id,
                    user_id=command.correlation_id,
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
        
        activity_map = {
            "sedentary": ActivityLevel.SEDENTARY,
            "lightly_active": ActivityLevel.LIGHT,
            "moderately_active": ActivityLevel.MODERATE,
            "very_active": ActivityLevel.ACTIVE,
            "extra_active": ActivityLevel.EXTRA
        }
        
        goal_map = {
            "lose_weight": Goal.CUTTING,
            "maintain_weight": Goal.MAINTENANCE,
            "gain_weight": Goal.BULKING,
            "build_muscle": Goal.BULKING
        }
        
        tdee_request = TdeeRequest(
            age=command.age,
            sex=sex,
            height_cm=command.height,
            weight_kg=command.weight,
            activity_level=activity_map.get(command.activity_level, ActivityLevel.MODERATE),
            goal=goal_map.get(command.goal, Goal.MAINTENANCE),
            unit_system=UnitSystem.METRIC
        )
        
        tdee_result = self.tdee_service.calculate_tdee(tdee_request)
        
        # Calculate target calories
        if tdee_request.goal == Goal.CUTTING:
            target_calories = tdee_result.tdee * 0.8
        elif tdee_request.goal == Goal.BULKING:
            target_calories = tdee_result.tdee * 1.15
        else:
            target_calories = tdee_result.tdee
        
        # Calculate macros
        macros = self.tdee_service.calculate_macros(
            tdee=target_calories,
            goal=tdee_request.goal,
            weight_kg=command.weight
        )
        
        return {
            "target_calories": round(target_calories, 0),
            "macros": SimpleMacroTargets(
                protein=round(macros.protein, 1),
                carbs=round(macros.carbs, 1),
                fat=round(macros.fat, 1)
            )
        }
    
    def _format_meal(self, meal) -> Dict[str, Any]:
        """Format meal for response."""
        prep_time = meal.preparation_time.get("prep", 0) if meal.preparation_time else 0
        cook_time = meal.preparation_time.get("cook", 0) if meal.preparation_time else 0
        total_time = meal.preparation_time.get("total", prep_time + cook_time) if meal.preparation_time else prep_time + cook_time
        
        # Extract dietary tags
        tags = meal.tags or []
        is_vegetarian = "vegetarian" in tags
        is_vegan = "vegan" in tags
        is_gluten_free = "gluten-free" in tags
        
        # Extract cuisine type
        cuisine_type = None
        for tag in tags:
            if tag not in ["vegetarian", "vegan", "gluten-free", "high-protein", "low-carb"]:
                cuisine_type = tag
                break
        
        return {
            "meal_id": meal.id,
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
            "instructions": meal.instructions or [],
            "is_vegetarian": is_vegetarian,
            "is_vegan": is_vegan,
            "is_gluten_free": is_gluten_free,
            "cuisine_type": cuisine_type
        }


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
            user_data["target_macros"] = tdee_result["macros"]
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