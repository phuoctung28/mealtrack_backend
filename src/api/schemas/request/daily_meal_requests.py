"""
Daily meal suggestion request DTOs.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MealTypeEnum(str, Enum):
    """Enum for meal types."""
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"

class UserPreferencesRequest(BaseModel):
    """Request DTO for user preferences from onboarding data."""
    age: int = Field(..., ge=13, le=120, description="User age")
    gender: str = Field(..., pattern="^(male|female|other)$", description="User gender")
    height: float = Field(..., gt=0, le=300, description="Height in cm")
    weight: float = Field(..., gt=0, le=500, description="Weight in kg")
    activity_level: str = Field(
        ..., 
        pattern="^(sedentary|lightly_active|moderately_active|very_active|extra_active)$",
        description="Activity level"
    )
    goal: str = Field(
        ..., 
        pattern="^(lose_weight|maintain_weight|gain_weight|build_muscle)$",
        description="Fitness goal"
    )
    dietary_preferences: Optional[List[str]] = Field(
        default_factory=list, 
        description="Dietary preferences/restrictions (vegetarian, vegan, etc.)"
    )
    health_conditions: Optional[List[str]] = Field(
        default_factory=list, 
        description="Health conditions (diabetes, hypertension, etc.)"
    )
    target_calories: Optional[float] = Field(
        None, 
        ge=1000, 
        le=5000,
        description="Daily calorie target (will be calculated if not provided)"
    )
    target_protein: Optional[float] = Field(None, ge=0, description="Target protein in grams")
    target_carbs: Optional[float] = Field(None, ge=0, description="Target carbs in grams")
    target_fat: Optional[float] = Field(None, ge=0, description="Target fat in grams")
    
    class Config:
        json_schema_extra = {
            "example": {
                "age": 25,
                "gender": "male",
                "height": 180.0,
                "weight": 75.0,
                "activity_level": "moderately_active",
                "goal": "build_muscle",
                "dietary_preferences": ["vegetarian"],
                "health_conditions": [],
                "target_calories": 2800
            }
        }

