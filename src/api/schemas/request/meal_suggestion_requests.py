"""
Request schemas for meal suggestion generation.
"""

import warnings
from enum import Enum
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class MealSizeEnum(str, Enum):
    """DEPRECATED: T-shirt sizing for meal portions. Use MealPortionTypeEnum."""

    S = "S"  # 10% of daily TDEE
    M = "M"  # 20%
    L = "L"  # 40%
    XL = "XL"  # 60%
    OMAD = "OMAD"  # 100%


class MealPortionTypeEnum(str, Enum):
    """Simplified meal portion types (replaces MealSizeEnum)."""

    SNACK = "snack"  # Fixed ~150-300 kcal
    MAIN = "main"  # Calculated from TDEE / meals_per_day
    OMAD = "omad"  # DEPRECATED — kept for backward compatibility with older mobile versions


def map_legacy_size_to_type(size: MealSizeEnum) -> MealPortionTypeEnum:
    """Map legacy meal size to new portion type."""
    mapping = {
        MealSizeEnum.S: MealPortionTypeEnum.SNACK,
        MealSizeEnum.M: MealPortionTypeEnum.SNACK,
        MealSizeEnum.L: MealPortionTypeEnum.MAIN,
        MealSizeEnum.XL: MealPortionTypeEnum.MAIN,
        MealSizeEnum.OMAD: MealPortionTypeEnum.OMAD,
    }
    return mapping[size]


class CookingTimeEnum(int, Enum):
    """Predefined cooking time options."""

    QUICK = 20
    MEDIUM = 30
    STANDARD = 45
    LONG = 60


class MealSuggestionRequest(BaseModel):
    """
    Request schema for generating meal suggestions.

    Generates exactly 3 meal suggestions based on:
    - meal_type, meal_portion_type (or legacy meal_size), ingredients, cooking_time

    Language preference is read from Accept-Language header (not from request body).

    If session_id is provided, generates NEW suggestions excluding previously shown meals.
    """

    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ..., description="Type of meal to generate suggestions for"
    )
    # NEW: Simplified portion type (preferred)
    meal_portion_type: Optional[MealPortionTypeEnum] = Field(
        None,
        description="Portion type: snack (~225 kcal), main (TDEE-based), omad (full daily)",
    )
    # DEPRECATED: Keep for backward compatibility
    meal_size: Optional[MealSizeEnum] = Field(
        None, description="DEPRECATED: Use meal_portion_type instead"
    )
    ingredients: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="Optional list of available ingredients (max 20)",
    )
    ingredient_image_url: Optional[str] = Field(
        None, description="Optional photo of ingredients for AI recognition"
    )
    cooking_time_minutes: Optional[CookingTimeEnum] = Field(
        None,
        description="Cooking time constraint (20/30/45/60 minutes). If omitted, no time limit.",
    )
    dietary_preferences: List[str] = Field(
        default_factory=list,
        description="Optional dietary preferences (e.g., vegetarian, vegan, halal)",
    )
    calorie_target: Optional[int] = Field(
        None,
        gt=0,
        description="Optional calorie target override (calculated from portion type if not provided)",
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for regeneration (automatically excludes previously shown meals)",
    )
    servings: int = Field(
        default=1,
        ge=1,
        le=4,
        description="DEPRECATED: Server now strictly generates 1 serving per suggestion. Field kept for backward compatibility with older clients.",
    )
    cooking_equipment: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="Available cooking equipment (e.g., Air fryer, Microwave, Pan)",
    )
    exclude_ids: List[str] = Field(
        default_factory=list,
        description="DEPRECATED: Use session_id instead for automatic exclusion",
    )
    cuisine_region: Optional[str] = Field(
        None,
        description="Preferred cuisine region (Asian, Western, Latin, Mediterranean). If omitted, diverse cuisines used.",
    )
    protein_target: Optional[float] = Field(
        None, ge=0, description="Optional protein target override in grams"
    )
    carbs_target: Optional[float] = Field(
        None, ge=0, description="Optional carbs target override in grams"
    )
    fat_target: Optional[float] = Field(
        None, ge=0, description="Optional fat target override in grams"
    )

    @field_validator("meal_size", mode="before")
    @classmethod
    def warn_deprecated_meal_size(cls, v):
        if v is not None:
            warnings.warn(
                "meal_size is deprecated, use meal_portion_type instead",
                DeprecationWarning,
                stacklevel=2,
            )
        return v

    def get_effective_portion_type(self) -> MealPortionTypeEnum:
        """Get effective portion type, preferring new field over legacy."""
        if self.meal_portion_type is not None:
            return self.meal_portion_type
        if self.meal_size is not None:
            return map_legacy_size_to_type(self.meal_size)
        # Default based on meal_type
        if self.meal_type == "snack":
            return MealPortionTypeEnum.SNACK
        return MealPortionTypeEnum.MAIN

    class Config:
        json_schema_extra = {
            "example": {
                "meal_type": "lunch",
                "meal_portion_type": "main",
                "ingredients": ["chicken breast", "broccoli", "rice"],
                "cooking_time_minutes": 30,
            }
        }


class DiscoverMealsRequest(BaseModel):
    """Request schema for discovery endpoint — generates 6 meals per batch."""

    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ..., description="Type of meal"
    )
    meal_portion_type: Optional[MealPortionTypeEnum] = Field(
        None, description="Portion type: snack, main, omad"
    )
    ingredients: List[str] = Field(
        default_factory=list, max_length=20,
        description="Optional available ingredients (max 20)",
    )
    cooking_time_minutes: Optional[CookingTimeEnum] = Field(
        None, description="Cooking time constraint",
    )
    cuisine_region: Optional[str] = Field(
        None, description="Preferred cuisine region",
    )
    calorie_target: Optional[int] = Field(
        None, gt=0, description="Override calorie target",
    )
    protein_target: Optional[float] = Field(None, ge=0)
    carbs_target: Optional[float] = Field(None, ge=0)
    fat_target: Optional[float] = Field(None, ge=0)
    session_id: Optional[str] = Field(
        None, description="Session ID for load-more (auto-excludes shown meals)",
    )
    batch_size: int = Field(
        default=10, ge=1, le=12, description="Meals per batch (default 10, max 12)",
    )

    def get_effective_portion_type(self) -> MealPortionTypeEnum:
        if self.meal_portion_type is not None:
            return self.meal_portion_type
        if self.meal_type == "snack":
            return MealPortionTypeEnum.SNACK
        return MealPortionTypeEnum.MAIN


class GenerateRecipesRequest(BaseModel):
    """Request to generate full recipes for 1-3 selected discovery meals."""

    meal_names: List[str] = Field(
        ..., min_length=1, max_length=3,
        description="English meal names from discovery grid (1-3)",
    )
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ..., description="Type of meal"
    )
    calorie_target: Optional[int] = Field(None, gt=0)
    cuisine_region: Optional[str] = None
    ingredients: List[str] = Field(default_factory=list, max_length=20)
    cooking_time_minutes: Optional[int] = Field(None, ge=5, le=120)
    protein_target: Optional[float] = Field(None, ge=0)
    carbs_target: Optional[float] = Field(None, ge=0)
    fat_target: Optional[float] = Field(None, ge=0)


class SaveInstructionItem(BaseModel):
    """A single cooking instruction step with optional duration."""

    instruction: str = Field(..., description="Instruction text")
    duration_minutes: Optional[int] = Field(
        None, ge=0, description="Estimated duration in minutes"
    )


class SaveIngredientItem(BaseModel):
    """
    A single ingredient with quantity, unit, and optional per-item macros.

    Per-ingredient macros default to 0 when the caller does not have them (e.g.
    when saving directly from an AI suggestion). They should be populated when
    available (e.g. from a local nutrition DB lookup) so that later ingredient
    edits can recalculate meal-level totals correctly.
    """

    name: str = Field(..., description="Ingredient name")
    amount: float = Field(..., gt=0, description="Quantity/amount")
    unit: str = Field(..., description="Unit (g, ml, tbsp, tsp, etc.)")
    calories: float = Field(
        default=0.0, ge=0, description="Calories for this ingredient (0 if unknown)"
    )
    protein: float = Field(
        default=0.0, ge=0, description="Protein in grams (0 if unknown)"
    )
    carbs: float = Field(
        default=0.0, ge=0, description="Carbohydrates in grams (0 if unknown)"
    )
    fat: float = Field(
        default=0.0, ge=0, description="Fat in grams (0 if unknown)"
    )


class SaveMealSuggestionRequest(BaseModel):
    """
    Request schema for saving a meal suggestion as a regular meal.
    """

    suggestion_id: str = Field(..., description="ID of the suggestion being saved")
    name: str = Field(..., description="Name of the meal")
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ..., description="Type of meal"
    )
    calories: Optional[int] = Field(
        None,
        gt=0,
        description="Total calories. If omitted, derived from macros (protein*4 + carbs*4 + fat*9).",
    )
    protein: float = Field(..., ge=0, description="Protein in grams (already scaled)")
    carbs: float = Field(
        ..., ge=0, description="Carbohydrates in grams (already scaled)"
    )
    fat: float = Field(..., ge=0, description="Fat in grams (already scaled)")
    description: Optional[str] = Field(None, description="Meal description")
    estimated_cook_time_minutes: Optional[int] = Field(
        None, ge=0, description="Estimated cooking time in minutes"
    )
    ingredients: List[SaveIngredientItem] = Field(
        default_factory=list,
        description="Structured ingredient list with name, amount, and unit",
    )
    instructions: List[Union[str, SaveInstructionItem]] = Field(
        default_factory=list,
        description="Cooking instructions as strings or {instruction, duration_minutes} objects",
    )
    portion_multiplier: int = Field(
        default=1,
        ge=1,
        description="Number of servings (informational only, values already scaled by AI)",
    )
    meal_date: str = Field(
        ..., description="Target date for the meal (YYYY-MM-DD format)"
    )
    cuisine_type: Optional[str] = Field(None, description="Cuisine type (e.g., Asian, Vietnamese)")
    origin_country: Optional[str] = Field(None, description="Country of origin")
    emoji: Optional[str] = Field(None, description="AI-assigned food emoji")
    unsplash_download_location: Optional[str] = Field(
        None, description="Unsplash download_location URL — triggers download event per API guidelines"
    )

    @field_validator("meal_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date format is YYYY-MM-DD."""
        from datetime import datetime

        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("meal_date must be in YYYY-MM-DD format")

    class Config:
        json_schema_extra = {
            "example": {
                "suggestion_id": "suggestion_123",
                "name": "Grilled Chicken Salad",
                "meal_type": "lunch",
                "calories": 450,
                "protein": 35.0,
                "carbs": 25.0,
                "fat": 20.0,
                "description": "Healthy grilled chicken salad",
                "estimated_cook_time_minutes": 30,
                "ingredients_list": ["chicken breast", "lettuce", "tomatoes"],
                "instructions": ["Grill chicken", "Chop vegetables", "Mix together"],
                "portion_multiplier": 1,
                "meal_date": "2024-01-15",
            }
        }
