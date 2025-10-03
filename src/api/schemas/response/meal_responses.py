"""
Meal-related response DTOs.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Union

from pydantic import BaseModel, Field


class MealStatusEnum(str, Enum):
    """Enum for meal processing status."""
    pending = "pending"
    analyzing = "analyzing"
    ready = "ready"
    failed = "failed"




class MacrosResponse(BaseModel):
    """Response DTO for macronutrient information."""
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams") 
    fat: float = Field(..., ge=0, description="Fat in grams")


class NutritionResponse(BaseModel):
    """Response DTO for nutrition information."""
    nutrition_id: str = Field(..., description="Nutrition record ID")
    calories: float = Field(..., ge=0, description="Calories")
    protein_g: float = Field(..., ge=0, description="Protein in grams")
    carbs_g: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat_g: float = Field(..., ge=0, description="Fat in grams")


class FoodItemResponse(BaseModel):
    """Response DTO for food item information."""
    id: str = Field(..., description="Food item ID")
    name: str = Field(..., description="Food item name")
    category: Optional[str] = Field(None, description="Food category")
    quantity: float = Field(..., description="Quantity")
    unit: str = Field(..., description="Unit of measurement")
    description: Optional[str] = Field(None, description="Description")
    nutrition: Optional[NutritionResponse] = Field(None, description="Nutrition information")


class SimpleMealResponse(BaseModel):
    """Response DTO for basic meal information."""
    meal_id: str = Field(..., description="Meal ID")
    status: MealStatusEnum = Field(..., description="Processing status")
    dish_name: Optional[str] = Field(None, description="Identified dish name")
    ready_at: Optional[datetime] = Field(None, description="When analysis completed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class DetailedMealResponse(SimpleMealResponse):
    """Response DTO for detailed meal information with nutrition."""
    food_items: List[FoodItemResponse] = Field(
        default_factory=list, 
        description="Food items in the meal"
    )
    image_url: Optional[str] = Field(None, description="Meal image URL")
    total_calories: Optional[float] = Field(None, ge=0, description="Total calories")
    total_weight_grams: Optional[float] = Field(None, gt=0, description="Total weight")
    total_nutrition: Optional[MacrosResponse] = Field(None, description="Total macros")


class MealListResponse(BaseModel):
    """Response DTO for paginated meal list."""
    meals: List[Union[SimpleMealResponse, DetailedMealResponse]] = Field(
        ..., 
        description="List of meals"
    )
    total: int = Field(..., ge=0, description="Total number of meals")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages")


class MealPhotoAnalysisResponse(BaseModel):
    """Response DTO for meal photo analysis."""
    meal_id: str = Field(..., description="ID of the analyzed meal")
    status: MealStatusEnum = Field(..., description="Analysis status")
    message: str = Field(..., description="Status message")
    estimated_completion_seconds: Optional[int] = Field(
        None, 
        description="Estimated seconds until completion"
    )


class MealSearchResponse(BaseModel):
    """Response DTO for meal search results."""
    results: List[SimpleMealResponse] = Field(..., description="Search results")
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., ge=0, description="Total matching results")


class NutritionSummaryResponse(BaseModel):
    """Response DTO for simplified nutrition summary."""
    meal_name: str = Field(..., description="Identified meal name")
    total_calories: float = Field(..., ge=0, description="Total calories")
    total_weight_grams: float = Field(..., gt=0, description="Total weight in grams")
    calories_per_100g: float = Field(..., ge=0, description="Calories per 100g")
    macros_per_100g: MacrosResponse = Field(..., description="Macronutrients per 100g")
    total_macros: MacrosResponse = Field(..., description="Total macronutrients")
    confidence_score: float = Field(..., ge=0, le=1, description="AI analysis confidence")


class ManualMealCreationResponse(BaseModel):
    """Response DTO for manual meal creation."""
    meal_id: str = Field(..., description="Created meal ID")
    status: str = Field(..., description="Creation status")
    message: str = Field(..., description="Success message")
    created_at: datetime = Field(..., description="Creation timestamp")