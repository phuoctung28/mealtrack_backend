"""
Meal-related response DTOs.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Union, Dict

from pydantic import BaseModel, ConfigDict, Field


def _serialize_datetime_utc(v: datetime) -> str:
    """Serialize datetime to ISO format with UTC timezone suffix."""
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.isoformat()


class MealStatusEnum(str, Enum):
    """Enum for meal processing status."""

    pending = "pending"
    analyzing = "analyzing"
    ready = "ready"
    failed = "failed"


# Translation Response DTOs


class ParsedFoodItem(BaseModel):
    """Response DTO for a single parsed food item."""

    name: str = Field(..., description="Food name")
    quantity: float = Field(..., ge=0, description="Amount")
    unit: str = Field(..., description="Serving unit (localized)")
    calories: float = Field(..., ge=0, description="Calories")
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat: float = Field(..., ge=0, description="Fat in grams")
    fiber: float = Field(0, ge=0, description="Fiber in grams")
    sugar: float = Field(0, ge=0, description="Sugar in grams")
    data_source: Optional[str] = Field(
        None, description="Data source: usda, fatsecret, or ai_estimate"
    )
    fdc_id: Optional[int] = Field(None, description="USDA FDC ID when available")


class ParseMealTextResponse(BaseModel):
    """Response DTO for parsed meal text."""

    items: List[ParsedFoodItem] = Field(..., description="Parsed food items")
    total_calories: float = Field(..., description="Total calories")
    total_protein: float = Field(..., description="Total protein in grams")
    total_carbs: float = Field(..., description="Total carbohydrates in grams")
    total_fat: float = Field(..., description="Total fat in grams")
    emoji: Optional[str] = Field(None, description="AI-assigned dish emoji")


class TranslatedFoodItemResponse(BaseModel):
    """Response DTO for translated food item."""

    id: str = Field(..., description="Food item ID")
    name: str = Field(..., description="Translated food item name")
    description: Optional[str] = Field(None, description="Translated description")


class MealTranslationResponse(BaseModel):
    """Response DTO for meal translation."""

    language: str = Field(..., description="ISO 639-1 language code")
    dish_name: str = Field(..., description="Translated dish name")
    meal_instruction: Optional[List[dict]] = Field(
        None, description="Translated instructions: [{instruction, duration_minutes}]"
    )
    meal_ingredients: Optional[List[str]] = Field(
        None, description="Translated ingredient names in food-item order"
    )
    food_items: List[TranslatedFoodItemResponse] = Field(
        default_factory=list, description="Translated food items (legacy)"
    )
    translated_at: Optional[datetime] = Field(
        None, description="When translation was performed"
    )


class MacrosResponse(BaseModel):
    """Response DTO for macronutrient information."""

    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat: float = Field(..., ge=0, description="Fat in grams")
    fiber: float = Field(0, ge=0, description="Fiber in grams")
    sugar: float = Field(0, ge=0, description="Sugar in grams")


class NutritionResponse(BaseModel):
    """Response DTO for nutrition information."""

    nutrition_id: str = Field(..., description="Nutrition record ID")
    calories: float = Field(..., ge=0, description="Calories")
    protein_g: float = Field(..., ge=0, description="Protein in grams")
    carbs_g: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat_g: float = Field(..., ge=0, description="Fat in grams")
    fiber_g: float = Field(0, ge=0, description="Fiber in grams")
    sugar_g: float = Field(0, ge=0, description="Sugar in grams")


class CustomNutritionResponse(BaseModel):
    """Response DTO for custom nutrition per 100g."""

    calories_per_100g: float = Field(..., description="Calories per 100g")
    protein_per_100g: float = Field(..., description="Protein per 100g")
    carbs_per_100g: float = Field(..., description="Carbs per 100g")
    fat_per_100g: float = Field(..., description="Fat per 100g")


class FoodItemResponse(BaseModel):
    """Response DTO for food item information."""

    id: str = Field(..., description="Food item ID")
    name: str = Field(..., description="Food item name")
    category: Optional[str] = Field(None, description="Food category")
    quantity: float = Field(..., description="Quantity")
    unit: str = Field(..., description="Unit of measurement")
    description: Optional[str] = Field(None, description="Description")
    nutrition: Optional[NutritionResponse] = Field(
        None, description="Nutrition information"
    )
    custom_nutrition: Optional[CustomNutritionResponse] = Field(
        None, description="Custom nutrition per 100g for custom ingredients"
    )
    fdc_id: Optional[int] = Field(None, description="USDA FDC ID if available")
    is_custom: bool = Field(False, description="Whether this is a custom ingredient")


class SimpleMealResponse(BaseModel):
    """Response DTO for basic meal information."""

    meal_id: str = Field(..., description="Meal ID")
    status: MealStatusEnum = Field(..., description="Processing status")
    dish_name: Optional[str] = Field(None, description="Identified dish name")
    emoji: Optional[str] = Field(None, description="AI-assigned food emoji")
    meal_type: Optional[str] = Field(
        None, description="Meal type (breakfast, lunch, dinner, snack)"
    )
    ready_at: Optional[datetime] = Field(None, description="When analysis completed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(json_encoders={datetime: _serialize_datetime_utc})


class DetailedMealResponse(SimpleMealResponse):
    """Response DTO for detailed meal information with nutrition."""

    food_items: List[FoodItemResponse] = Field(
        default_factory=list, description="Food items in the meal"
    )
    image_url: Optional[str] = Field(None, description="Meal image URL")
    total_calories: Optional[float] = Field(None, ge=0, description="Total calories")
    total_weight_grams: Optional[float] = Field(None, gt=0, description="Total weight")
    total_nutrition: Optional[MacrosResponse] = Field(None, description="Total macros")
    translations: Optional[Dict[str, MealTranslationResponse]] = Field(
        None, description="Translations keyed by language code"
    )
    # Recipe details (populated for AI suggestions, null for scanned/manual meals)
    description: Optional[str] = Field(None, description="Meal description")
    instructions: Optional[List[dict]] = Field(
        None, description="Structured recipe steps: [{instruction, duration_minutes}]"
    )
    prep_time_min: Optional[int] = Field(None, description="Prep time in minutes")
    cook_time_min: Optional[int] = Field(None, description="Cook time in minutes")
    cuisine_type: Optional[str] = Field(None, description="Cuisine type")
    origin_country: Optional[str] = Field(None, description="Country of origin")


class MealListResponse(BaseModel):
    """Response DTO for paginated meal list."""

    meals: List[Union[SimpleMealResponse, DetailedMealResponse]] = Field(
        ..., description="List of meals"
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
        None, description="Estimated seconds until completion"
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
    confidence_score: float = Field(
        ..., ge=0, le=1, description="AI analysis confidence"
    )


class ManualMealCreationResponse(BaseModel):
    """Response DTO for manual meal creation."""

    meal_id: str = Field(..., description="Created meal ID")
    status: str = Field(..., description="Creation status")
    message: str = Field(..., description="Success message")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(json_encoders={datetime: _serialize_datetime_utc})
