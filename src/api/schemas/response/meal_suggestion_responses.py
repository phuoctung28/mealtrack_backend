"""
Response schemas for meal suggestion generation (Phase 06).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MacrosSchema(BaseModel):
    """Macronutrient information."""

    calories: float = Field(..., description="Total calories")
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")


class MacroEstimateResponse(BaseModel):
    """Alias for MacrosSchema for consistency."""

    calories: float = Field(..., description="Total calories")
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")


class IngredientResponse(BaseModel):
    """Ingredient with amount and unit."""

    name: str = Field(..., description="Ingredient name")
    amount: float = Field(..., description="Amount/quantity")
    unit: str = Field(..., description="Unit (g, ml, tbsp, etc)")


class RecipeStepResponse(BaseModel):
    """Single recipe step with numbered instruction."""

    step: int = Field(..., description="Step number (1-indexed)")
    instruction: str = Field(..., description="Step instruction")
    duration_minutes: Optional[int] = Field(None, description="Duration for this step")


class MealSuggestionResponse(BaseModel):
    """
    A single meal suggestion with full recipe details (Phase 06).
    """

    id: str = Field(..., description="Unique identifier for this suggestion")
    meal_name: str = Field(..., description="Name of the meal (possibly translated)")
    english_name: Optional[str] = Field(
        None,
        description="Original English name — stable reconciliation key across locales",
    )
    emoji: Optional[str] = Field(None, description="AI-assigned food emoji")
    description: str = Field(..., description="Brief description of the meal")
    macros: MacroEstimateResponse = Field(
        ..., description="Macronutrient breakdown (base portion)"
    )
    ingredients: List[IngredientResponse] = Field(
        ..., description="List of ingredients with amounts"
    )
    recipe_steps: List[RecipeStepResponse] = Field(
        ..., description="Numbered cooking steps"
    )
    prep_time_minutes: int = Field(
        ..., description="Total prep time (includes cooking)"
    )
    confidence_score: float = Field(
        default=0.9, ge=0.0, le=1.0, description="AI confidence score (0.0-1.0)"
    )
    origin_country: Optional[str] = Field(None, description="Country of origin (e.g., Vietnam, Italy)")
    cuisine_type: Optional[str] = Field(None, description="Cuisine type (e.g., Asian, Mediterranean)")


# Alias for backward compatibility
MealSuggestionItem = MealSuggestionResponse


class SuggestionsListResponse(BaseModel):
    """
    Response containing 1-3 meal suggestions (Phase 06).
    Note: May return fewer than 3 if some generations fail.
    """

    session_id: str = Field(..., description="Suggestion session ID for tracking")
    meal_type: str = Field(
        ..., description="Type of meal (breakfast, lunch, dinner, snack)"
    )
    meal_portion_type: str = Field(
        ..., description="Portion type: snack, main, or omad"
    )
    target_calories: float = Field(
        ..., description="Calculated target calories for this portion type"
    )
    suggestions: List[MealSuggestionResponse] = Field(
        ..., min_length=1, max_length=3, description="1-3 meal suggestions (may be partial if generation fails)"
    )
    suggestion_count: int = Field(
        ..., ge=1, le=3, description="Number of suggestions returned (1-3)"
    )
    expires_at: datetime = Field(
        ..., description="Session expiration timestamp (4 hours)"
    )


# Alias for backward compatibility
MealSuggestionsResponse = SuggestionsListResponse


class RecipeBatchResponse(BaseModel):
    """Response containing full recipes for 1-3 selected discovery meals."""

    recipes: List[MealSuggestionResponse] = Field(
        ..., min_length=1, max_length=3,
        description="Full recipe details for selected meals",
    )


class DiscoveryMealResponse(BaseModel):
    """Lightweight meal for discovery grid — name + macros + optional image."""

    id: str
    meal_name: str
    english_name: Optional[str] = Field(None, description="Original English name for recipe generation")
    macros: MacroEstimateResponse
    # Fields below are optional — not returned in lightweight discovery
    emoji: Optional[str] = None
    description: Optional[str] = None
    ingredient_names: Optional[List[str]] = Field(default=None, description="Ingredient names (only in full response)")
    prep_time_minutes: Optional[int] = None
    cuisine_type: Optional[str] = None
    origin_country: Optional[str] = None
    image_url: Optional[str] = Field(None, description="Food photo URL (hotlinked from Pexels/Unsplash)")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    image_source: Optional[str] = Field(None, description="Image provider: pexels | unsplash")
    photographer: Optional[str] = Field(None, description="Photographer name for attribution")
    photographer_url: Optional[str] = Field(None, description="Photographer profile URL with UTM params")
    unsplash_download_location: Optional[str] = Field(None, description="Unsplash download trigger URL (pass back on save)")


class DiscoveryBatchResponse(BaseModel):
    """Batch of discovery meals with session tracking."""

    session_id: str
    meals: List[DiscoveryMealResponse]
    has_more: bool = Field(default=True, description="Whether more batches can be loaded")
    meal_count: int


class FoodImageResponse(BaseModel):
    """Food image search result."""

    url: str = Field(..., description="Full-size image URL")
    thumbnail_url: str = Field(..., description="Thumbnail URL")
    source: str = Field(..., description="Image provider (pexels/unsplash)")
    photographer: Optional[str] = Field(None, description="Photographer name")


class SaveMealSuggestionResponse(BaseModel):
    """
    Response schema for saving a meal suggestion as a regular meal.
    """
    meal_id: str = Field(..., description="ID of the created meal")
    message: str = Field(..., description="Success message")
    meal_date: str = Field(..., description="Date the meal was saved for (YYYY-MM-DD)")

    class Config:
        json_schema_extra = {
            "example": {
                "meal_id": "meal_123",
                "message": "Meal suggestion saved successfully",
                "meal_date": "2024-01-15"
            }
        }
