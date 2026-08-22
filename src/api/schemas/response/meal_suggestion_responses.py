"""Response schemas for meal suggestion discovery, recipes, and saving."""


from pydantic import BaseModel, Field

from src.api.schemas.response.meal_responses import DetailedMealResponse


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
    food_reference_id: int | None = Field(
        None, description="Canonical food reference ID when resolved"
    )


class RecipeStepResponse(BaseModel):
    """Single recipe step with numbered instruction."""

    step: int = Field(..., description="Step number (1-indexed)")
    instruction: str = Field(..., description="Step instruction")
    duration_minutes: int | None = Field(None, description="Duration for this step")


class MealSuggestionResponse(BaseModel):
    """
    A single meal suggestion with full recipe details (Phase 06).
    """

    id: str = Field(..., description="Unique identifier for this suggestion")
    meal_name: str = Field(..., description="Name of the meal (possibly translated)")
    english_name: str | None = Field(
        None,
        description="Original English name — stable reconciliation key across locales",
    )
    emoji: str | None = Field(None, description="AI-assigned food emoji")
    description: str = Field(..., description="Brief description of the meal")
    macros: MacroEstimateResponse = Field(
        ..., description="Macronutrient breakdown (base portion)"
    )
    ingredients: list[IngredientResponse] = Field(
        ..., description="List of ingredients with amounts"
    )
    recipe_steps: list[RecipeStepResponse] = Field(
        ..., description="Numbered cooking steps"
    )
    prep_time_minutes: int = Field(
        ..., description="Total prep time (includes cooking)"
    )
    confidence_score: float = Field(
        default=0.9, ge=0.0, le=1.0, description="AI confidence score (0.0-1.0)"
    )
    origin_country: str | None = Field(
        None, description="Country of origin (e.g., Vietnam, Italy)"
    )
    cuisine_type: str | None = Field(
        None, description="Cuisine type (e.g., Asian, Mediterranean)"
    )


# Alias for backward compatibility
MealSuggestionItem = MealSuggestionResponse


class RecipeBatchResponse(BaseModel):
    """Response containing full recipes for 1-3 selected discovery meals."""

    recipes: list[MealSuggestionResponse] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="Full recipe details for selected meals",
    )


class DiscoveryMealResponse(BaseModel):
    """Lightweight meal for discovery grid — name + macros + optional image."""

    id: str
    meal_name: str
    english_name: str | None = Field(
        None, description="Original English name for recipe generation"
    )
    macros: MacroEstimateResponse
    # Fields below are optional — not returned in lightweight discovery
    emoji: str | None = None
    description: str | None = None
    ingredient_names: list[str] | None = Field(
        default=None, description="Ingredient names (only in full response)"
    )
    prep_time_minutes: int | None = None
    cuisine_type: str | None = None
    origin_country: str | None = None
    image_url: str | None = Field(
        None, description="Food photo URL (hotlinked from Pexels/Unsplash)"
    )
    thumbnail_url: str | None = Field(None, description="Thumbnail URL")
    image_source: str | None = Field(
        None, description="Image provider: pexels | unsplash"
    )
    photographer: str | None = Field(
        None, description="Photographer name for attribution"
    )
    photographer_url: str | None = Field(
        None, description="Photographer profile URL with UTM params"
    )
    unsplash_download_location: str | None = Field(
        None, description="Unsplash download trigger URL (pass back on save)"
    )
    image_confidence: float = Field(
        default=0.0, description="0.0–1.0 how well the image matches the meal name"
    )


class DiscoveryBatchResponse(BaseModel):
    """Batch of discovery meals with session tracking."""

    session_id: str
    meals: list[DiscoveryMealResponse]
    has_more: bool = Field(
        default=True, description="Whether more batches can be loaded"
    )
    meal_count: int


class SaveMealSuggestionResponse(BaseModel):
    """
    Response schema for saving a meal suggestion as a regular meal.
    """

    meal_id: str = Field(..., description="ID of the created meal")
    message: str = Field(..., description="Success message")
    meal_date: str = Field(..., description="Date the meal was saved for (YYYY-MM-DD)")
    meal_detail: DetailedMealResponse | None = Field(
        None, description="Created meal detail for immediate client-side caching"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "meal_id": "meal_123",
                "message": "Meal suggestion saved successfully",
                "meal_date": "2024-01-15",
                "meal_detail": None,
            }
        }
