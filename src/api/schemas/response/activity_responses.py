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



class ActivityResponse(BaseModel):
    """Generic activity response that can be either meal or workout."""

    id: str
    type: str
    timestamp: str
    title: str

    # Additional fields stored as dict for flexibility
    # This allows both meal and workout activities to use same response
    class Config:
        extra = "allow"
