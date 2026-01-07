"""
Response schemas for meal suggestion generation (Phase 06).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MacrosSchema(BaseModel):
    """Macronutrient information."""

    calories: int = Field(..., description="Total calories")
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")


class MacroEstimateResponse(BaseModel):
    """Alias for MacrosSchema for consistency."""

    calories: int = Field(..., description="Total calories")
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
    meal_name: str = Field(..., description="Name of the meal")
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
    target_calories: int = Field(
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


class AcceptedMealResponse(BaseModel):
    """Response after accepting suggestion with portion multiplier."""

    meal_id: str = Field(..., description="ID of saved meal in history")
    meal_name: str = Field(..., description="Name of the meal")
    macros: MacroEstimateResponse = Field(
        ..., description="Adjusted macros (after portion multiplier)"
    )
    saved_at: datetime = Field(..., description="Timestamp when meal was saved")

    class Config:
        json_schema_extra = {
            "example": {
                "meal_id": "meal_12345",
                "meal_name": "Grilled Chicken Rice Bowl",
                "macros": {"protein": 70.0, "carbs": 80.0, "fat": 30.0},
                "saved_at": "2025-12-30T12:00:00Z",
            }
        }


class SaveMealSuggestionResponse(BaseModel):
    """
    Response after saving a meal suggestion to history.
    (LEGACY - use AcceptedMealResponse instead)
    """

    success: bool = Field(..., description="Whether the save was successful")
    message: str = Field(..., description="Status message")
    meal_id: Optional[str] = Field(
        None, description="ID of the saved meal in the database"
    )
    meal_date: str = Field(..., description="Date the meal was saved for (YYYY-MM-DD)")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Meal suggestion saved successfully to your meal history",
                "meal_id": "12345",
                "meal_date": "2024-01-15",
            }
        }
