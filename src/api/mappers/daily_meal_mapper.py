"""
Mapper for daily meal suggestion DTOs and domain models.
"""
from datetime import date
from typing import Dict, Any

from src.api.schemas.request import UserPreferencesRequest
from src.api.schemas.response import (
    SuggestedMealResponse,
    DailyMealSuggestionsResponse,
    NutritionTotalsResponse
)
from src.domain.model.macro_targets import SimpleMacroTargets
from src.domain.model.meal_plan import PlannedMeal


class DailyMealMapper:
    """Mapper for daily meal suggestions."""
    
    @staticmethod
    def map_user_preferences_to_dict(request: UserPreferencesRequest) -> Dict[str, Any]:
        """
        Convert UserPreferencesRequest to dictionary for domain service.
        
        Args:
            request: User preferences from API request
            
        Returns:
            Dictionary with user preferences for domain service
        """
        return {
            "age": request.age,
            "gender": request.gender,
            "height": request.height,
            "weight": request.weight,
            "activity_level": request.activity_level,
            "goal": request.goal,
            "dietary_preferences": request.dietary_preferences or [],
            "health_conditions": request.health_conditions or [],
            "target_calories": request.target_calories,
            "target_macros": request.target_macros
        }
    
    @staticmethod
    def map_planned_meal_to_schema(meal: PlannedMeal) -> SuggestedMealResponse:
        """
        Convert PlannedMeal domain model to SuggestedMealSchema.
        
        Args:
            meal: PlannedMeal domain model
            
        Returns:
            SuggestedMealSchema DTO
        """
        # Extract preparation time components
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
        
        return SuggestedMealResponse(
            meal_id=meal.id,
            meal_type=meal.meal_type.value,
            name=meal.name,
            description=meal.description,
            prep_time=prep_time,
            cook_time=cook_time,
            total_time=total_time,
            calories=int(meal.calories),
            protein=meal.protein,
            carbs=meal.carbs,
            fat=meal.fat,
            ingredients=meal.ingredients,
            instructions=meal.instructions or [],
            is_vegetarian=is_vegetarian,
            is_vegan=is_vegan,
            is_gluten_free=is_gluten_free,
            cuisine_type=cuisine_type
        )
    
    @staticmethod
    def map_handler_response_to_dto(
        handler_response: Dict[str, Any],
        target_calories: float,
        target_macros: SimpleMacroTargets
    ) -> DailyMealSuggestionsResponse:
        """
        Convert handler response dictionary to DailyMealSuggestionsResponse.
        
        Args:
            handler_response: Response from daily meal suggestion handler
            target_calories: Target calories for the user
            target_macros: Target macros for the user
            
        Returns:
            DailyMealSuggestionsResponse DTO
        """
        # Map meals
        meals = []
        for meal_dict in handler_response.get("meals", []):
            # Create PlannedMeal from dict for easier mapping
            meal = PlannedMeal(
                id=meal_dict["meal_id"],
                meal_type=meal_dict["meal_type"],
                name=meal_dict["name"],
                description=meal_dict["description"],
                calories=meal_dict["calories"],
                protein=meal_dict["protein"],
                carbs=meal_dict["carbs"],
                fat=meal_dict["fat"],
                ingredients=meal_dict["ingredients"],
                instructions=meal_dict.get("instructions", []),
                preparation_time={
                    "prep": meal_dict.get("prep_time", 0),
                    "cook": meal_dict.get("cook_time", 0),
                    "total": meal_dict.get("total_time", 0)
                },
                tags=[]  # Tags will be reconstructed from boolean fields
            )
            
            # Add tags based on dietary flags
            if meal_dict.get("is_vegetarian"):
                meal.tags.append("vegetarian")
            if meal_dict.get("is_vegan"):
                meal.tags.append("vegan")
            if meal_dict.get("is_gluten_free"):
                meal.tags.append("gluten-free")
            if meal_dict.get("cuisine_type"):
                meal.tags.append(meal_dict["cuisine_type"])
            
            meals.append(DailyMealMapper.map_planned_meal_to_schema(meal))
        
        # Map nutrition totals
        daily_totals_dict = handler_response.get("daily_totals", {})
        daily_totals = NutritionTotalsResponse(
            calories=daily_totals_dict.get("calories", 0),
            protein=daily_totals_dict.get("protein", 0),
            carbs=daily_totals_dict.get("carbs", 0),
            fat=daily_totals_dict.get("fat", 0)
        )
        
        target_totals = NutritionTotalsResponse(
            calories=target_calories,
            protein=target_macros.protein,
            carbs=target_macros.carbs,
            fat=target_macros.fat
        )
        
        return DailyMealSuggestionsResponse(
            date=handler_response.get("date", date.today().isoformat()),
            meal_count=handler_response.get("meal_count", len(meals)),
            meals=meals,
            daily_totals=daily_totals,
            target_totals=target_totals
        )
    
    @staticmethod
    def map_to_suggestions_response(result: Dict[str, Any]) -> DailyMealSuggestionsResponse:
        """
        Map handler result to suggestions response.
        
        Args:
            result: Result from handler with meals and targets
            
        Returns:
            DailyMealSuggestionsResponse DTO
        """
        target_calories = result.get('target_calories', 2000)
        target_macros = result.get('target_macros')
        
        if target_macros and hasattr(target_macros, 'protein'):
            # It's already a SimpleMacroTargets object
            pass
        else:
            # Create default if not provided
            from src.domain.model.macro_targets import SimpleMacroTargets
            target_macros = SimpleMacroTargets(
                protein=50.0,
                carbs=250.0,
                fat=65.0
            )
        
        return DailyMealMapper.map_handler_response_to_dto(
            result,
            target_calories,
            target_macros
        )
    
    @staticmethod
    def map_to_single_meal_response(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map handler result to single meal response.
        
        Args:
            result: Result from handler with single meal
            
        Returns:
            Dictionary with meal data for SingleMealSuggestionResponse
        """
        return {"meal": result.get("meal", {})}