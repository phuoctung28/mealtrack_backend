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
    - meal_type, meal_portion_type (or legacy meal_size), ingredients, cooking_time
    
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
    exclude_ids: List[str] = Field(
        default_factory=list,
        description="DEPRECATED: Use session_id instead for automatic exclusion",
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


# DEPRECATED: RegenerateSuggestionsRequest is no longer needed.
# Use MealSuggestionRequest with session_id parameter to regenerate with automatic exclusion.
# 
# class RegenerateSuggestionsRequest(BaseModel):
#     """DEPRECATED: Use MealSuggestionRequest with session_id instead."""
#     session_id: str
#     exclude_ids: List[str] = Field(default_factory=list)


class SaveMealSuggestionRequest(BaseModel):
    """
    Request schema for saving a selected meal suggestion to meal history.
    """

    suggestion_id: str = Field(..., description="ID of the suggestion to save")
    name: str = Field(..., description="Name of the meal")
    description: str = Field(default="", description="Description of the meal")
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ..., description="Type of meal"
    )
    estimated_cook_time_minutes: int = Field(
        ..., description="Total cooking time in minutes"
    )
    calories: int = Field(..., description="Calories for the meal")
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")
    portion_multiplier: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Portion multiplier (1x, 2x, 3x, 4x) - scales macros before saving",
    )
    ingredients_list: List[str] = Field(
        default_factory=list, description="List of ingredients"
    )
    instructions: List[str] = Field(
        default_factory=list, description="Cooking instructions"
    )
    meal_date: Optional[str] = Field(
        None,
        description="Date to save the meal for (YYYY-MM-DD format), defaults to today",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "suggestion_id": "meal_lunch_1234",
                "name": "Grilled Chicken with Rice",
                "description": "Healthy high-protein lunch",
                "meal_type": "lunch",
                "estimated_cook_time_minutes": 25,
                "calories": 520,
                "protein": 45.0,
                "carbs": 55.0,
                "fat": 12.0,
                "portion_multiplier": 1,
                "ingredients_list": ["chicken breast", "brown rice", "broccoli"],
                "instructions": ["Grill chicken", "Cook rice", "Steam broccoli"],
                "meal_date": "2024-01-15",
            }
        }

