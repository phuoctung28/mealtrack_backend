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
from src.domain.model.meal_planning import PlannedMeal, MealType
from src.domain.model.meal_planning import SimpleMacroTargets


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
        # Build target_macros from individual fields if any are provided
        target_macros = None
        if any([request.target_protein, request.target_carbs, request.target_fat]):
            target_macros = {
                "protein": request.target_protein,
                "carbs": request.target_carbs,
                "fat": request.target_fat
            }
        
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
            "target_macros": target_macros
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
            # Convert meal_type string to enum
            meal_type_str = meal_dict["meal_type"]
            meal_type = MealType(meal_type_str) if isinstance(meal_type_str, str) else meal_type_str
            
            # Create PlannedMeal from dict for easier mapping
            meal = PlannedMeal(
                meal_type=meal_type,
                name=meal_dict["name"],
                description=meal_dict["description"],
                calories=meal_dict["calories"],
                protein=meal_dict["protein"],
                carbs=meal_dict["carbs"],
                fat=meal_dict["fat"],
                prep_time=meal_dict.get("prep_time", 0),
                cook_time=meal_dict.get("cook_time", 0),
                ingredients=meal_dict["ingredients"],
                instructions=meal_dict.get("instructions", []),
                is_vegetarian=meal_dict.get("is_vegetarian", False),
                is_vegan=meal_dict.get("is_vegan", False),
                is_gluten_free=meal_dict.get("is_gluten_free", False),
                cuisine_type=meal_dict.get("cuisine_type")
            )
            
            # Set extra attributes for mapper
            meal.id = meal_dict["meal_id"]
            meal.preparation_time = {
                "prep": meal_dict.get("prep_time", 0),
                "cook": meal_dict.get("cook_time", 0),
                "total": meal_dict.get("total_time", 0)
            }
            
            # Build tags from dietary flags
            tags = []
            if meal_dict.get("is_vegetarian"):
                tags.append("vegetarian")
            if meal_dict.get("is_vegan"):
                tags.append("vegan")
            if meal_dict.get("is_gluten_free"):
                tags.append("gluten-free")
            if meal_dict.get("cuisine_type"):
                tags.append(meal_dict["cuisine_type"])
            meal.tags = tags
            
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
        target_calories = result.get('target_calories')
        if not target_calories:
            raise ValueError("target_calories is required in result data. Ensure handler provides calculated TDEE data.")
        
        target_macros = result.get('target_macros')
        if not target_macros:
            raise ValueError("target_macros is required in result data. Ensure handler provides calculated TDEE macros.")
        
        # Convert macros dict to SimpleMacroTargets if needed
        if target_macros and hasattr(target_macros, 'protein'):
            # It's already a SimpleMacroTargets object
            pass
        elif isinstance(target_macros, dict):
            # Convert dict to SimpleMacroTargets object
            from src.domain.model.meal_planning import SimpleMacroTargets
            target_macros = SimpleMacroTargets(
                protein=target_macros.get('protein', 0.0),
                carbs=target_macros.get('carbs', 0.0),
                fat=target_macros.get('fat', 0.0)
            )
        else:
            raise ValueError("target_macros must be a dict or SimpleMacroTargets object with actual TDEE calculation data.")
        
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