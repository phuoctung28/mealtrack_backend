"""
Mapper for meal-related DTOs and domain models.
"""
from typing import List, Optional

from src.api.schemas.response import (
    SimpleMealResponse,
    DetailedMealResponse,
    MealListResponse,
    FoodItemResponse,
    NutritionResponse,
    MealStatusResponse
)
from src.api.schemas.response.daily_nutrition_response import DailyNutritionResponse
from src.domain.model.meal import Meal
from src.domain.model.nutrition import FoodItem, Nutrition

# Status mapping from domain to API
STATUS_MAPPING = {
    "PROCESSING": "pending",
    "ANALYZING": "analyzing", 
    "ENRICHING": "analyzing",
    "READY": "ready",
    "FAILED": "failed"
}


class MealMapper:
    """Mapper for meal data transformation."""
    
    @staticmethod
    def to_simple_response(meal: Meal) -> SimpleMealResponse:
        """
        Convert Meal domain model to SimpleMealResponse DTO.
        
        Args:
            meal: Meal domain model
            
        Returns:
            SimpleMealResponse DTO
        """
        return SimpleMealResponse(
            meal_id=meal.meal_id,
            status=STATUS_MAPPING.get(meal.status.value, meal.status.value.lower()),
            dish_name=meal.dish_name,
            ready_at=meal.ready_at,
            error_message=meal.error_message,
            created_at=meal.created_at
        )
    
    @staticmethod
    def to_detailed_response(meal: Meal, image_url: Optional[str] = None) -> DetailedMealResponse:
        """
        Convert Meal domain model to DetailedMealResponse DTO.
        
        Args:
            meal: Meal domain model
            image_url: Optional image URL
            
        Returns:
            DetailedMealResponse DTO
        """
        from src.api.schemas.response.meal_responses import MacrosResponse
        
        # Map food items from nutrition if available
        food_items = []
        total_calories = 0
        total_nutrition = None
        
        if meal.nutrition:
            total_calories = meal.nutrition.calories
            
            # Map total nutrition macros
            if hasattr(meal.nutrition, 'macros') and meal.nutrition.macros:
                total_nutrition = MacrosResponse(
                    protein=meal.nutrition.macros.protein,
                    carbs=meal.nutrition.macros.carbs,
                    fat=meal.nutrition.macros.fat,
                )
            # Handle legacy structure where nutrition has direct properties
            elif hasattr(meal.nutrition, 'protein'):
                total_nutrition = MacrosResponse(
                    protein=meal.nutrition.protein,
                    carbs=meal.nutrition.carbs,
                    fat=meal.nutrition.fat,
                )
            
            # Map food items
            if meal.nutrition.food_items:
                for item in meal.nutrition.food_items:
                    nutrition_dto = None
                    if hasattr(item, 'macros') and item.macros:
                        nutrition_dto = NutritionResponse(
                            nutrition_id=str(item.name),  # Use name as ID since FoodItem doesn't have ID
                            calories=item.calories,
                            protein_g=item.macros.protein,
                            carbs_g=item.macros.carbs,
                            fat_g=item.macros.fat,
                            sugar_g=None,
                            sodium_mg=None
                        )
                    
                    food_item_dto = FoodItemResponse(
                        food_item_id=str(item.name),  # Use name as ID
                        name=item.name,
                        category=None,
                        quantity=item.quantity,
                        unit=item.unit,
                        description=None,
                        nutrition=nutrition_dto
                    )
                    food_items.append(food_item_dto)
        
        return DetailedMealResponse(
            meal_id=meal.meal_id,
            status=STATUS_MAPPING.get(meal.status.value, meal.status.value.lower()),
            dish_name=meal.dish_name,
            ready_at=meal.ready_at,
            error_message=meal.error_message,
            created_at=meal.created_at,
            updated_at=None,  # Meal domain model doesn't have updated_at
            food_items=food_items,
            image_url=image_url,
            total_calories=total_calories,
            total_weight_grams=meal.weight_grams if hasattr(meal, 'weight_grams') else None,
            total_nutrition=total_nutrition
        )
    
    @staticmethod
    def to_meal_list_response(
        meals: List[Meal], 
        total: int,
        page: int = 1,
        page_size: int = 10,
        image_urls: Optional[dict] = None
    ) -> MealListResponse:
        """
        Convert list of Meal domain models to MealListResponse DTO.
        
        Args:
            meals: List of Meal domain models
            total: Total count of meals
            page: Current page number
            page_size: Items per page
            image_urls: Optional dict mapping meal_id to image URLs
            
        Returns:
            MealListResponse DTO
        """
        image_urls = image_urls or {}
        
        meal_responses = []
        for meal in meals:
            if meal.nutrition and meal.nutrition.food_items:  # Has detailed info
                response = MealMapper.to_detailed_response(
                    meal, 
                    image_urls.get(meal.meal_id)
                )
            else:  # Simple response
                response = MealMapper.to_simple_response(meal)
            meal_responses.append(response)
        
        return MealListResponse(
            meals=meal_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
    
    @staticmethod
    def map_nutrition_from_dict(nutrition_dict: dict) -> Nutrition:
        """
        Create Nutrition domain model from dictionary.
        
        Args:
            nutrition_dict: Dictionary with nutrition data
            
        Returns:
            Nutrition domain model
        """
        return Nutrition(
            nutrition_id=nutrition_dict.get("nutrition_id", ""),
            calories=nutrition_dict.get("calories", 0),
            protein_g=nutrition_dict.get("protein_g", 0),
            carbs_g=nutrition_dict.get("carbs_g", 0),
            fat_g=nutrition_dict.get("fat_g", 0),
            sugar_g=nutrition_dict.get("sugar_g", 0),
            sodium_mg=nutrition_dict.get("sodium_mg", 0)
        )
    
    @staticmethod
    def map_food_item_from_dict(item_dict: dict) -> FoodItem:
        """
        Create FoodItem domain model from dictionary.
        
        Args:
            item_dict: Dictionary with food item data
            
        Returns:
            FoodItem domain model
        """
        nutrition = None
        if "nutrition" in item_dict and item_dict["nutrition"]:
            nutrition = MealMapper.map_nutrition_from_dict(item_dict["nutrition"])
        
        return FoodItem(
            food_item_id=item_dict.get("food_item_id", ""),
            name=item_dict.get("name", ""),
            category=item_dict.get("category", ""),
            quantity=item_dict.get("quantity", 0),
            unit=item_dict.get("unit", ""),
            description=item_dict.get("description"),
            nutrition=nutrition
        )
    
    @staticmethod
    def to_status_response(meal: Meal) -> MealStatusResponse:
        """
        Convert Meal domain model to MealStatusResponse DTO.
        
        Args:
            meal: Meal domain model
            
        Returns:
            MealStatusResponse DTO
        """
        # Get user-friendly status message
        status_messages = {
            "PROCESSING": "Your meal is being processed",
            "ANALYZING": "AI is analyzing your meal",
            "ENRICHING": "Enhancing your meal data",
            "READY": "Your meal analysis is ready",
            "FAILED": "Analysis failed"
        }
        
        return MealStatusResponse(
            meal_id=meal.meal_id,
            status=STATUS_MAPPING.get(meal.status.value, meal.status.value.lower()),
            status_message=status_messages.get(meal.status.value, "Unknown status"),
            error_message=meal.error_message
        )
    
    @staticmethod
    def to_daily_nutrition_response(daily_macros_data: dict) -> DailyNutritionResponse:
        """
        Convert daily macros query result to DailyNutritionResponse DTO.
        
        Args:
            daily_macros_data: Dictionary with daily macros data from query
            
        Returns:
            DailyNutritionResponse DTO
        """
        from src.api.schemas.response.daily_nutrition_response import MacrosResponse
        
        # Extract data - require actual user targets, no hardcoded defaults
        target_calories = daily_macros_data.get("target_calories")
        if not target_calories:
            raise ValueError("target_calories is required. Daily macros query must include user's calculated TDEE data.")
        
        target_macros = MacrosResponse(
            protein=daily_macros_data.get("target_macros").get("protein") or 0.0,
            carbs=daily_macros_data.get("target_macros").get("carbs") or 0.0, 
            fat=daily_macros_data.get("target_macros").get("fat") or 0.0,
        )
        
        consumed_macros = MacrosResponse(
            protein=daily_macros_data.get("total_protein", 0.0),
            carbs=daily_macros_data.get("total_carbs", 0.0),
            fat=daily_macros_data.get("total_fat", 0.0),
        )

        consumed_calories = daily_macros_data.get("total_calories", 0.0)

        # Calculate remaining macros
        remaining_calories = max(0, target_calories - consumed_calories)
        remaining_macros = MacrosResponse(
            protein=max(0, target_macros.protein - consumed_macros.protein),
            carbs=max(0, target_macros.carbs - consumed_macros.carbs),
            fat=max(0, target_macros.fat - consumed_macros.fat),
        )
        
        # Calculate completion percentages
        completion_percentage = {
            "calories": (consumed_calories / target_calories * 100) if target_calories > 0 else 0,
            "protein": (consumed_macros.protein / target_macros.protein * 100) if target_macros.protein > 0 else 0,
            "carbs": (consumed_macros.carbs / target_macros.carbs * 100) if target_macros.carbs > 0 else 0,
            "fat": (consumed_macros.fat / target_macros.fat * 100) if target_macros.fat > 0 else 0
        }
        
        return DailyNutritionResponse(
            date=daily_macros_data.get("date", ""),
            target_calories=target_calories,
            target_macros=target_macros,
            consumed_calories=consumed_calories,
            consumed_macros=consumed_macros,
            remaining_calories=remaining_calories,
            remaining_macros=remaining_macros,
            completion_percentage=completion_percentage,
        )