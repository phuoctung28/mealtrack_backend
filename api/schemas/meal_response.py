from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from domain.model.meal import Meal, MealStatus


class MacrosResponse(BaseModel):
    """Response schema for macronutrients."""
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = None


class MicrosResponse(BaseModel):
    """Response schema for micronutrients."""
    # Add micronutrients as needed
    pass


class FoodItemResponse(BaseModel):
    """Response schema for a food item in a meal."""
    name: str
    quantity: float
    unit: str
    calories: float
    macros: MacrosResponse
    confidence: Optional[float] = None


class NutritionResponse(BaseModel):
    """Response schema for meal nutrition data."""
    calories: float
    macros: MacrosResponse
    food_items: Optional[List[FoodItemResponse]] = None
    confidence_score: Optional[float] = None


class MealImageResponse(BaseModel):
    """Response schema for meal image data."""
    image_id: str
    format: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    url: Optional[str] = None


class MealStatusResponse(BaseModel):
    """Response schema for meal status."""
    meal_id: str
    status: str
    status_message: str
    error_message: Optional[str] = None


class MealResponse(BaseModel):
    """Response schema for meal data."""
    meal_id: str
    status: str
    created_at: datetime
    image: MealImageResponse
    nutrition: Optional[NutritionResponse] = None
    error_message: Optional[str] = None
    ready_at: Optional[datetime] = None
    raw_gpt_json: Optional[str] = None
    
    @classmethod
    def from_domain(cls, meal: Meal) -> "MealResponse":
        """
        Convert a domain Meal model to a response schema.
        
        Args:
            meal: Domain meal model
            
        Returns:
            MealResponse schema
        """
        # Create image response
        image_response = MealImageResponse(
            image_id=meal.image.image_id,
            format=meal.image.format,
            size_bytes=meal.image.size_bytes,
            width=meal.image.width,
            height=meal.image.height,
            url=meal.image.url if hasattr(meal.image, 'url') else None
        )
        
        # Create nutrition response if available
        nutrition_response = None
        if meal.nutrition:
            # Create macros response
            macros_response = MacrosResponse(
                protein=meal.nutrition.macros.protein,
                carbs=meal.nutrition.macros.carbs,
                fat=meal.nutrition.macros.fat,
                fiber=meal.nutrition.macros.fiber
            )
            
            # Create food items response if available
            food_items_response = None
            if meal.nutrition.food_items:
                food_items_response = []
                for food_item in meal.nutrition.food_items:
                    food_macros = MacrosResponse(
                        protein=food_item.macros.protein,
                        carbs=food_item.macros.carbs,
                        fat=food_item.macros.fat,
                        fiber=food_item.macros.fiber
                    )
                    
                    food_item_response = FoodItemResponse(
                        name=food_item.name,
                        quantity=food_item.quantity,
                        unit=food_item.unit,
                        calories=food_item.calories,
                        macros=food_macros,
                        confidence=food_item.confidence
                    )
                    
                    food_items_response.append(food_item_response)
            
            # Create complete nutrition response
            nutrition_response = NutritionResponse(
                calories=meal.nutrition.calories,
                macros=macros_response,
                food_items=food_items_response,
                confidence_score=meal.nutrition.confidence_score
            )
        
        # Create complete meal response
        return cls(
            meal_id=meal.meal_id,
            status=meal.status.value,
            created_at=meal.created_at,
            image=image_response,
            nutrition=nutrition_response,
            error_message=meal.error_message,
            ready_at=getattr(meal, "ready_at", None),
            raw_gpt_json=getattr(meal, "raw_gpt_json", None)
        ) 