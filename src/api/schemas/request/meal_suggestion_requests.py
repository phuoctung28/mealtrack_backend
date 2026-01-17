"""
Request schemas for meal suggestion generation.
"""

import warnings
from enum import Enum
from typing import List, Literal, Optional

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
    OMAD = "omad"  # Full daily target


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
    - meal_type, meal_portion_type (or legacy meal_size), ingredients, cooking_time, language
    
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
    cooking_time_minutes: CookingTimeEnum = Field(
        ..., description="Cooking time constraint (20/30/45/60 minutes)"
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
        description="Number of servings (1-4). Ingredient amounts and calories scale accordingly.",
    )
    exclude_ids: List[str] = Field(
        default_factory=list,
        description="DEPRECATED: Use session_id instead for automatic exclusion",
    )
    language: str = Field(
        default="en",
        description="ISO 639-1 language code for meal suggestions (en, vi, es, fr, de, ja, zh)",
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

    @field_validator("language")
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        """Validate language code and fallback to 'en' if invalid."""
        valid_languages = {"en", "vi", "es", "fr", "de", "ja", "zh"}
        normalized = v.lower().strip()
        if normalized not in valid_languages:
            warnings.warn(
                f"Unsupported language code '{v}', falling back to 'en'",
                UserWarning,
                stacklevel=2,
            )
            return "en"
        return normalized

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


# DEPRECATED: RegenerateSuggestionsRequest is no longer needed.
# Use MealSuggestionRequest with session_id parameter to regenerate with automatic exclusion.
# 
# class RegenerateSuggestionsRequest(BaseModel):
#     """DEPRECATED: Use MealSuggestionRequest with session_id instead."""
#     session_id: str
#     exclude_ids: List[str] = Field(default_factory=list)


class SaveMealSuggestionRequest(BaseModel):
    """
    Request schema for saving a meal suggestion to planned_meals table.
    This adds the meal to the user's daily meal plan (suggested meals).
    """
    suggestion_id: str = Field(..., description="ID of the suggestion being saved")
    name: str = Field(..., description="Name of the meal")
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ..., description="Type of meal"
    )
    calories: int = Field(..., gt=0, description="Total calories (already scaled by AI for selected servings)")
    protein: float = Field(..., ge=0, description="Protein in grams (already scaled)")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams (already scaled)")
    fat: float = Field(..., ge=0, description="Fat in grams (already scaled)")
    description: Optional[str] = Field(None, description="Meal description")
    estimated_cook_time_minutes: Optional[int] = Field(
        None, ge=0, description="Estimated cooking time in minutes"
    )
    ingredients_list: List[str] = Field(
        default_factory=list, description="List of ingredients as strings"
    )
    instructions: List[str] = Field(
        default_factory=list, description="List of cooking instructions"
    )
    portion_multiplier: int = Field(
        default=1, ge=1, description="Number of servings (informational only, values already scaled by AI)"
    )
    meal_date: str = Field(
        ..., description="Target date for the meal (YYYY-MM-DD format)"
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
                "meal_date": "2024-01-15"
            }
        }

