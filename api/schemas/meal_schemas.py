from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class MacrosSchema(BaseModel):
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams") 
    fat: float = Field(..., ge=0, description="Fat in grams")
    fiber: Optional[float] = Field(None, ge=0, description="Fiber in grams")

# Meal Creation and Update Schemas
class CreateMealRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Meal name")
    description: Optional[str] = Field(None, max_length=500, description="Meal description")
    weight_grams: Optional[float] = Field(None, gt=0, description="Weight in grams")
    calories_per_100g: Optional[float] = Field(None, ge=0, description="Calories per 100g")
    macros_per_100g: Optional[MacrosSchema] = Field(None, description="Macros per 100g")

class UpdateMealRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Meal name")
    description: Optional[str] = Field(None, max_length=500, description="Meal description")
    weight_grams: Optional[float] = Field(None, gt=0, description="Weight in grams")
    calories_per_100g: Optional[float] = Field(None, ge=0, description="Calories per 100g")
    macros_per_100g: Optional[MacrosSchema] = Field(None, description="Macros per 100g")

class UpdateMealMacrosRequest(BaseModel):
    weight_grams: float = Field(..., gt=0, le=5000, description="Weight of the meal portion in grams (must be between 0 and 5000g)")

# Photo Analysis Schemas
class MealPhotoResponse(BaseModel):
    meal_id: str = Field(..., description="ID of the analyzed meal")
    meal_name: str = Field(..., description="Identified meal name")
    confidence: float = Field(..., ge=0, le=1, description="AI confidence score")
    macros: MacrosSchema = Field(..., description="Calculated macronutrients")
    calories: float = Field(..., ge=0, description="Total calories")
    status: str = Field(..., description="Processing status")

# Simplified Nutrition Schema
class NutritionSummary(BaseModel):
    """Simplified nutrition summary with gram-based measurements."""
    meal_name: str = Field(..., description="Identified meal name")
    total_calories: float = Field(..., ge=0, description="Total calories for the portion")
    total_weight_grams: float = Field(..., gt=0, description="Total weight of the meal in grams")
    calories_per_100g: float = Field(..., ge=0, description="Calories per 100g")
    macros_per_100g: MacrosSchema = Field(..., description="Macronutrients per 100g")
    total_macros: MacrosSchema = Field(..., description="Total macronutrients for the portion")
    confidence_score: float = Field(..., ge=0, le=1, description="AI analysis confidence")

# Response Schemas
class MealResponse(BaseModel):
    meal_id: str
    name: Optional[str] = None
    dish_name: Optional[str] = None
    description: Optional[str] = None
    weight_grams: Optional[float] = None
    total_calories: Optional[float] = None
    calories_per_100g: Optional[float] = None
    macros_per_100g: Optional[MacrosSchema] = None
    total_macros: Optional[MacrosSchema] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    error_message: Optional[str] = None
    image_url: Optional[str] = None

class MealStatusResponse(BaseModel):
    meal_id: str
    status: str
    status_message: str
    error_message: Optional[str] = None

class PaginatedMealResponse(BaseModel):
    meals: List[MealResponse]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int

class MealSearchRequest(BaseModel):
    query: str = Field(..., min_length=0, max_length=200)
    limit: int = Field(10, ge=1, le=100)
    include_ingredients: bool = Field(False, description="Include ingredients in search")

class MealSearchResponse(BaseModel):
    results: List[MealResponse]
    query: str
    total_results: int

class MealImageResponse(BaseModel):
    """Response schema for meal image data."""
    image_id: str
    format: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    url: Optional[str] = None

class DetailedMealResponse(BaseModel):
    """Detailed response schema for meal data with simplified nutrition summary."""
    meal_id: str
    status: str
    created_at: datetime
    image: MealImageResponse
    dish_name: Optional[str] = None
    nutrition: Optional[NutritionSummary] = None
    error_message: Optional[str] = None
    ready_at: Optional[datetime] = None
    
    @classmethod
    def from_domain(cls, meal):
        """Convert a domain Meal model to a response schema."""
        # Create image response
        image_response = MealImageResponse(
            image_id=meal.image.image_id,
            format=meal.image.format,
            size_bytes=meal.image.size_bytes,
            width=meal.image.width,
            height=meal.image.height,
            url=meal.image.url if hasattr(meal.image, 'url') else None
        )
        
        # Create simplified nutrition response if available
        nutrition_response = None
        if meal.nutrition:
            # Get dish_name from raw_gpt_json if available
            meal_name = "Unknown Meal"
            if hasattr(meal, 'raw_gpt_json') and meal.raw_gpt_json:
                try:
                    import json
                    raw_data = json.loads(meal.raw_gpt_json)
                    # Handle both direct JSON and wrapped response formats
                    if isinstance(raw_data, dict):
                        if 'structured_data' in raw_data:
                            meal_name = raw_data['structured_data'].get('dish_name', meal_name)
                        else:
                            meal_name = raw_data.get('dish_name', meal_name)
                except (json.JSONDecodeError, KeyError):
                    pass

            # Check if meal has been updated with new weight
            if hasattr(meal, 'updated_weight_grams'):
                estimated_weight = meal.updated_weight_grams
            else:
                estimated_weight = 300.0  # Default estimated weight in grams
                
                if hasattr(meal.nutrition, 'food_items') and meal.nutrition.food_items:
                    first_food = meal.nutrition.food_items[0]
                    # Try to extract weight from quantity if unit suggests weight
                    if first_food.unit and 'g' in first_food.unit.lower():
                        estimated_weight = first_food.quantity
                    elif first_food.quantity > 10:  # Assume grams if quantity is large
                        estimated_weight = first_food.quantity
            
            # Create macros response
            macros_response = MacrosSchema(
                protein=meal.nutrition.macros.protein,
                carbs=meal.nutrition.macros.carbs,
                fat=meal.nutrition.macros.fat,
                fiber=meal.nutrition.macros.fiber if hasattr(meal.nutrition.macros, 'fiber') else None
            )
            
            # Calculate nutrition values based on current weight
            if hasattr(meal, 'updated_weight_grams') and hasattr(meal, 'original_weight_grams'):
                # Meal has been updated - scale nutrition accordingly
                ratio = meal.updated_weight_grams / meal.original_weight_grams
                total_calories = meal.nutrition.calories * ratio
                total_macros = MacrosSchema(
                    protein=macros_response.protein * ratio,
                    carbs=macros_response.carbs * ratio,
                    fat=macros_response.fat * ratio,
                    fiber=macros_response.fiber * ratio if macros_response.fiber else None
                )
            else:
                # Use original nutrition values
                total_calories = meal.nutrition.calories
                total_macros = macros_response
            
            # Calculate per-100g values
            weight_ratio = estimated_weight / 100.0
            calories_per_100g = total_calories / weight_ratio if weight_ratio > 0 else total_calories
            macros_per_100g = MacrosSchema(
                protein=total_macros.protein / weight_ratio if weight_ratio > 0 else total_macros.protein,
                carbs=total_macros.carbs / weight_ratio if weight_ratio > 0 else total_macros.carbs,
                fat=total_macros.fat / weight_ratio if weight_ratio > 0 else total_macros.fat,
                fiber=total_macros.fiber / weight_ratio if weight_ratio > 0 and total_macros.fiber else total_macros.fiber
            )
            
            # Create simplified nutrition summary
            nutrition_response = NutritionSummary(
                meal_name=meal_name,
                total_calories=total_calories,
                total_weight_grams=estimated_weight,
                calories_per_100g=calories_per_100g,
                macros_per_100g=macros_per_100g,
                total_macros=total_macros,
                confidence_score=meal.nutrition.confidence_score
            )
        
        # Create complete meal response
        return cls(
            meal_id=meal.meal_id,
            status=meal.status.value,
            created_at=meal.created_at,
            image=image_response,
            dish_name=meal.dish_name,
            nutrition=nutrition_response,
            error_message=meal.error_message,
            ready_at=getattr(meal, "ready_at", None)
        ) 