"""
Meal DTOs (Data Transfer Objects) for API requests and responses.

This module contains:
- Request DTOs for meal operations
- Response DTOs for meal data
- Search and filtering DTOs
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models import MacrosSchema, NutritionSummarySchema
from .base import BaseRequest, BaseResponse, TimestampedResponse, ImageSchema


# ============================================================================
# Request DTOs
# ============================================================================

class CreateMealRequest(BaseRequest):
    """DTO for creating a new meal."""
    name: str = Field(..., min_length=1, max_length=200, description="Meal name")
    description: Optional[str] = Field(None, max_length=500, description="Meal description")
    weight_grams: Optional[float] = Field(None, gt=0, description="Weight in grams")
    calories_per_100g: Optional[float] = Field(None, ge=0, description="Calories per 100g")
    macros_per_100g: Optional[MacrosSchema] = Field(None, description="Macros per 100g")


class UpdateMealRequest(BaseRequest):
    """DTO for updating an existing meal."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Meal name")
    description: Optional[str] = Field(None, max_length=500, description="Meal description")
    weight_grams: Optional[float] = Field(None, gt=0, description="Weight in grams")
    calories_per_100g: Optional[float] = Field(None, ge=0, description="Calories per 100g")
    macros_per_100g: Optional[MacrosSchema] = Field(None, description="Macros per 100g")


class UpdateMealMacrosRequest(BaseRequest):
    """DTO for updating meal macros with weight adjustment."""
    weight_grams: float = Field(
        ..., 
        gt=0, 
        le=5000, 
        description="Weight of the meal portion in grams (must be between 0 and 5000g)"
    )


class MealSearchRequest(BaseRequest):
    """DTO for searching meals."""
    query: str = Field(..., min_length=0, max_length=200)
    limit: int = Field(10, ge=1, le=100)
    include_ingredients: bool = Field(False, description="Include ingredients in search")


# ============================================================================
# Response DTOs
# ============================================================================

class MealResponse(TimestampedResponse):
    """Standard meal response DTO."""
    meal_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    weight_grams: Optional[float] = None
    total_calories: Optional[float] = None
    calories_per_100g: Optional[float] = None
    macros_per_100g: Optional[MacrosSchema] = None
    total_macros: Optional[MacrosSchema] = None
    status: str
    ready_at: Optional[datetime] = None
    error_message: Optional[str] = None
    image_url: Optional[str] = None


class MealStatusResponse(BaseResponse):
    """Lightweight meal status response DTO."""
    meal_id: str
    status: str
    status_message: str
    error_message: Optional[str] = None


class IngredientBreakdownSchema(BaseModel):
    """Schema for individual ingredient breakdown from AI analysis."""
    name: str = Field(..., description="Ingredient name")
    quantity: float = Field(..., description="Ingredient quantity")
    unit: str = Field(..., description="Unit of measurement") 
    calories: float = Field(..., ge=0, description="Calories for this ingredient")
    macros: MacrosSchema = Field(..., description="Macros for this ingredient")


class DetailedMealResponse(TimestampedResponse):
    """Detailed meal response with nutrition and image data."""
    meal_id: str
    status: str
    image: ImageSchema
    nutrition: Optional[NutritionSummarySchema] = None
    ingredients: Optional[List[IngredientBreakdownSchema]] = Field(None, description="AI-analyzed ingredient breakdown")
    error_message: Optional[str] = None
    ready_at: Optional[datetime] = None


class MealPhotoResponse(BaseResponse):
    """Response for meal photo analysis."""
    meal_id: str = Field(..., description="ID of the analyzed meal")
    meal_name: str = Field(..., description="Identified meal name")
    confidence: float = Field(..., ge=0, le=1, description="AI confidence score")
    macros: MacrosSchema = Field(..., description="Calculated macronutrients")
    calories: float = Field(..., ge=0, description="Total calories")
    status: str = Field(..., description="Processing status")


# ============================================================================
# Collection DTOs
# ============================================================================

class PaginatedMealResponse(BaseResponse):
    """Paginated collection of meals."""
    meals: List[MealResponse]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int


class MealSearchResponse(BaseResponse):
    """Search results for meals."""
    results: List[MealResponse]
    query: str
    total_results: int 