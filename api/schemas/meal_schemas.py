from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator


class MacrosSchema(BaseModel):
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams") 
    fat: float = Field(..., ge=0, description="Fat in grams")
    fiber: Optional[float] = Field(None, ge=0, description="Fiber in grams")

# Meal Creation and Update Schemas
class CreateMealRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Meal name")
    description: Optional[str] = Field(None, max_length=500, description="Meal description")
    serving_size: Optional[float] = Field(None, gt=0, description="Serving size")
    serving_unit: Optional[str] = Field(None, max_length=50, description="Serving unit (e.g., 'cup', 'piece')")
    calories_per_serving: Optional[float] = Field(None, ge=0, description="Calories per serving")
    macros_per_serving: Optional[MacrosSchema] = Field(None, description="Macros per serving")

class UpdateMealRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Meal name")
    description: Optional[str] = Field(None, max_length=500, description="Meal description")
    serving_size: Optional[float] = Field(None, gt=0, description="Serving size")
    serving_unit: Optional[str] = Field(None, max_length=50, description="Serving unit")
    calories_per_serving: Optional[float] = Field(None, ge=0, description="Calories per serving")
    macros_per_serving: Optional[MacrosSchema] = Field(None, description="Macros per serving")

class UpdateMealMacrosRequest(BaseModel):
    size: Optional[float] = Field(None, gt=0, description="Size/amount of meal")
    amount: Optional[float] = Field(None, gt=0, description="Amount of meal")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measurement")
    
    @validator('size', 'amount')
    def at_least_one_required(cls, v, values):
        if v is None and values.get('size') is None and values.get('amount') is None:
            raise ValueError('At least one of size or amount must be provided')
        return v

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
    """Simplified nutrition summary without detailed food items breakdown."""
    meal_name: str = Field(..., description="Identified meal name")
    calories: float = Field(..., ge=0, description="Total calories")
    macros: MacrosSchema = Field(..., description="Macronutrients breakdown")
    serving_info: Optional[str] = Field(None, description="Serving size information (e.g., '1 bowl', '2 pieces')")
    confidence_score: float = Field(..., ge=0, le=1, description="AI analysis confidence")

# Response Schemas
class MealResponse(BaseModel):
    meal_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    serving_size: Optional[float] = None
    serving_unit: Optional[str] = None
    calories_per_serving: Optional[float] = None
    macros_per_serving: Optional[MacrosSchema] = None
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
            # Extract meal name from first food item or use a default
            meal_name = "Unknown Meal"
            serving_info = None
            
            if hasattr(meal.nutrition, 'food_items') and meal.nutrition.food_items:
                first_food = meal.nutrition.food_items[0]
                meal_name = first_food.name
                serving_info = f"{first_food.quantity} {first_food.unit}"
            
            # Create macros response
            macros_response = MacrosSchema(
                protein=meal.nutrition.macros.protein,
                carbs=meal.nutrition.macros.carbs,
                fat=meal.nutrition.macros.fat,
                fiber=meal.nutrition.macros.fiber if hasattr(meal.nutrition.macros, 'fiber') else None
            )
            
            # Create simplified nutrition summary
            nutrition_response = NutritionSummary(
                meal_name=meal_name,
                calories=meal.nutrition.calories,
                macros=macros_response,
                serving_info=serving_info,
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
            ready_at=getattr(meal, "ready_at", None)
        ) 