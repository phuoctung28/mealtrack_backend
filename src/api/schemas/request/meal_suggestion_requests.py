"""
Request schemas for meal suggestion generation.
"""
from datetime import datetime
from typing import List, Optional, Literal
from enum import Enum

from pydantic import BaseModel, Field


class MealSizeEnum(str, Enum):
    """T-shirt sizing for meal portions."""
    S = "S"      # 10% of daily TDEE
    M = "M"      # 20%
    L = "L"      # 40%
    XL = "XL"    # 60%
    OMAD = "OMAD"  # 100%


class CookingTimeEnum(int, Enum):
    """Predefined cooking time options."""
    QUICK = 20
    MEDIUM = 30
    STANDARD = 45
    LONG = 60


class MealSuggestionRequest(BaseModel):
    """
    Request schema for generating meal suggestions (Phase 06).

    Generates exactly 3 meal suggestions based on:
    - meal_type, meal_size, ingredients (text or image), cooking_time
    """

    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ...,
        description="Type of meal to generate suggestions for"
    )
    meal_size: MealSizeEnum = Field(
        ...,
        description="T-shirt sizing (S/M/L/XL/OMAD) determines % of daily TDEE"
    )
    ingredients: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="Optional list of available ingredients (max 20)"
    )
    ingredient_image_url: Optional[str] = Field(
        None,
        description="Optional photo of ingredients for AI recognition"
    )
    cooking_time_minutes: CookingTimeEnum = Field(
        ...,
        description="Cooking time constraint (20/30/45/60 minutes)"
    )
    dietary_preferences: List[str] = Field(
        default_factory=list,
        description="Optional dietary preferences (e.g., vegetarian, vegan, halal)"
    )
    calorie_target: Optional[int] = Field(
        None,
        gt=0,
        description="Optional calorie target override (calculated from meal_size if not provided)"
    )
    exclude_ids: List[str] = Field(
        default_factory=list,
        description="List of meal IDs to exclude (for regeneration)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "meal_type": "lunch",
                "meal_size": "M",
                "ingredients": ["chicken breast", "broccoli", "rice"],
                "ingredient_image_url": None,
                "cooking_time_minutes": 30,
                "dietary_preferences": ["high-protein"],
                "calorie_target": None,
                "exclude_ids": []
            }
        }


class RegenerateSuggestionsRequest(BaseModel):
    """Request to regenerate 3 NEW meal ideas (excludes shown)."""

    session_id: str = Field(..., description="Suggestion session ID")
    exclude_ids: List[str] = Field(
        default_factory=list,
        description="Suggestion IDs to exclude from regeneration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "exclude_ids": ["meal_lunch_1234", "meal_lunch_5678"]
            }
        }


class AcceptSuggestionRequest(BaseModel):
    """Request to accept suggestion with portion multiplier."""

    portion_multiplier: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Portion multiplier (1x, 2x, 3x, 4x)"
    )
    consumed_at: Optional[datetime] = Field(
        None,
        description="Optional consumption timestamp (defaults to now)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "portion_multiplier": 2,
                "consumed_at": "2025-12-30T12:00:00Z"
            }
        }


class RejectSuggestionRequest(BaseModel):
    """Request to reject suggestion with optional feedback."""

    feedback: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional feedback on why suggestion was rejected"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "feedback": "Too spicy for my taste"
            }
        }


class SaveMealSuggestionRequest(BaseModel):
    """
    Request schema for saving a selected meal suggestion to meal history.
    (LEGACY - use AcceptSuggestionRequest instead)
    """

    suggestion_id: str = Field(
        ...,
        description="ID of the suggestion to save"
    )
    name: str = Field(
        ...,
        description="Name of the meal"
    )
    description: str = Field(
        default="",
        description="Description of the meal"
    )
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ...,
        description="Type of meal"
    )
    estimated_cook_time_minutes: int = Field(
        ...,
        description="Total cooking time in minutes"
    )
    calories: int = Field(
        ...,
        description="Calories for the meal"
    )
    protein: float = Field(
        ...,
        description="Protein in grams"
    )
    carbs: float = Field(
        ...,
        description="Carbohydrates in grams"
    )
    fat: float = Field(
        ...,
        description="Fat in grams"
    )
    ingredients_list: List[str] = Field(
        default_factory=list,
        description="List of ingredients"
    )
    instructions: List[str] = Field(
        default_factory=list,
        description="Cooking instructions"
    )
    meal_date: Optional[str] = Field(
        None,
        description="Date to save the meal for (YYYY-MM-DD format), defaults to today"
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
                "ingredients_list": ["chicken breast", "brown rice", "broccoli"],
                "instructions": ["Grill chicken", "Cook rice", "Steam broccoli"],
                "meal_date": "2024-01-15"
            }
        }

