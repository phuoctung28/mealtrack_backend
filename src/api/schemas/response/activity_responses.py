"""
Response schemas for activity endpoints.
"""

from typing import Optional

from pydantic import BaseModel


class MacrosResponse(BaseModel):
    """Macronutrient information."""

    protein: float
    carbs: float
    fat: float
    fiber: float = 0.0
    sugar: float = 0.0


class MealActivityResponse(BaseModel):
    """Response schema for meal activity."""

    id: str
    type: str = "meal"
    timestamp: str
    title: str
    emoji: Optional[str] = None
    meal_type: str
    calories: float
    macros: MacrosResponse
    quantity: float
    status: str
    image_url: Optional[str] = None



