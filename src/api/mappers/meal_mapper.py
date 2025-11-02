"""
Mapper for meal-related DTOs and domain models.
"""
from typing import List, Optional

from src.api.schemas.response import (
    SimpleMealResponse,
    DetailedMealResponse,
    MealListResponse,
    FoodItemResponse,
    NutritionResponse
)
from src.api.schemas.response.daily_nutrition_response import DailyNutritionResponse
from src.domain.model.meal import Meal
from src.domain.model.nutrition import FoodItem, Nutrition, Macros, Micros

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
                from src.api.schemas.response.meal_responses import CustomNutritionResponse
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
                    
                    # Calculate per-100g custom nutrition if this is a custom ingredient or has no fdc_id
                    custom_nutrition_dto = None
                    if hasattr(item, 'is_custom') and item.is_custom and item.quantity > 0:
                        # Calculate per-100g values from absolute values
                        scale_factor = 100.0 / item.quantity
                        custom_nutrition_dto = CustomNutritionResponse(
                            calories_per_100g=item.calories * scale_factor,
                            protein_per_100g=item.macros.protein * scale_factor if item.macros else 0.0,
                            carbs_per_100g=item.macros.carbs * scale_factor if item.macros else 0.0,
                            fat_per_100g=item.macros.fat * scale_factor if item.macros else 0.0,
                        )
                    
                    food_item_dto = FoodItemResponse(
                        id=str(item.id),  # Use the primary key ID as string
                        name=item.name,
                        category=None,
                        quantity=item.quantity,
                        unit=item.unit,
                        description=None,
                        nutrition=nutrition_dto,
                        custom_nutrition=custom_nutrition_dto,
                        fdc_id=getattr(item, 'fdc_id', None),
                        is_custom=getattr(item, 'is_custom', False)
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
        macros = Macros(
            protein=nutrition_dict.get("protein_g", 0),
            carbs=nutrition_dict.get("carbs_g", 0),
            fat=nutrition_dict.get("fat_g", 0)
        )
        
        micros = None
        if "sodium_mg" in nutrition_dict:
            micros = Micros(
                sodium=nutrition_dict.get("sodium_mg", 0)
            )
        
        return Nutrition(
            calories=nutrition_dict.get("calories", 0),
            macros=macros,
            micros=micros,
            food_items=[]
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
        # Extract calories and macros from nutrition dict if present
        calories = item_dict.get("calories", 0)
        macros = Macros(protein=0, carbs=0, fat=0)
        micros = None
        
        if "nutrition" in item_dict and item_dict["nutrition"]:
            nutrition_data = item_dict["nutrition"]
            calories = nutrition_data.get("calories", 0)
            macros = Macros(
                protein=nutrition_data.get("protein_g", 0),
                carbs=nutrition_data.get("carbs_g", 0),
                fat=nutrition_data.get("fat_g", 0)
            )
            if "sodium_mg" in nutrition_data:
                micros = Micros(sodium=nutrition_data.get("sodium_mg", 0))
        
        return FoodItem(
            id=item_dict.get("id", ""),
            name=item_dict.get("name", ""),
            quantity=item_dict.get("quantity", 0),
            unit=item_dict.get("unit", ""),
            calories=calories,
            macros=macros,
            micros=micros,
            confidence=item_dict.get("confidence", 1.0),
            fdc_id=item_dict.get("fdc_id"),
            is_custom=item_dict.get("is_custom", False)
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
        from src.api.exceptions import ResourceNotFoundException
        
        # Extract data - require actual user targets, no hardcoded defaults
        target_calories = daily_macros_data.get("target_calories")
        if not target_calories:
            raise ResourceNotFoundException(
                message="User profile not found or incomplete. Please complete onboarding first.",
                error_code="TDEE_DATA_NOT_FOUND",
                details={
                    "user_id": daily_macros_data.get("user_id"),
                    "reason": "User has not completed onboarding or TDEE calculation is missing"
                }
            )
        
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