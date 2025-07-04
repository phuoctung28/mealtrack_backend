"""
Mapper for meal-related DTOs and domain models.
"""
from typing import List, Optional
from datetime import datetime

from src.api.schemas.response import (
    SimpleMealResponse,
    DetailedMealResponse,
    MealListResponse,
    FoodItemResponse,
    NutritionResponse,
    MacrosResponse
)
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.nutrition import FoodItem, Nutrition


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
            status=meal.status.value,
            dish_name=meal.dish_name,
            ready_at=meal.ready_at,
            error_message=meal.error_message,
            created_at=meal.created_at,
            updated_at=meal.updated_at
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
        # Map food items
        food_items = []
        for item in meal.food_items:
            nutrition_dto = None
            if item.nutrition:
                nutrition_dto = NutritionResponse(
                    nutrition_id=item.nutrition.nutrition_id,
                    calories=item.nutrition.calories,
                    protein_g=item.nutrition.protein_g,
                    carbs_g=item.nutrition.carbs_g,
                    fat_g=item.nutrition.fat_g,
                    fiber_g=item.nutrition.fiber_g,
                    sugar_g=item.nutrition.sugar_g,
                    sodium_mg=item.nutrition.sodium_mg
                )
            
            food_item_dto = FoodItemResponse(
                fooditem_id=item.fooditem_id,
                name=item.name,
                category=item.category,
                quantity=item.quantity,
                unit=item.unit,
                description=item.description,
                nutrition=nutrition_dto
            )
            food_items.append(food_item_dto)
        
        return DetailedMealResponse(
            meal_id=meal.meal_id,
            status=meal.status.value,
            dish_name=meal.dish_name,
            ready_at=meal.ready_at,
            error_message=meal.error_message,
            created_at=meal.created_at,
            updated_at=meal.updated_at,
            food_items=food_items,
            image_url=image_url
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
            if meal.food_items:  # Has detailed info
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
            fiber_g=nutrition_dict.get("fiber_g", 0),
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
            fooditem_id=item_dict.get("fooditem_id", ""),
            name=item_dict.get("name", ""),
            category=item_dict.get("category", ""),
            quantity=item_dict.get("quantity", 0),
            unit=item_dict.get("unit", ""),
            description=item_dict.get("description"),
            nutrition=nutrition
        )