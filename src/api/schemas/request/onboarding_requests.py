from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class TrainingLevelEnum(str, Enum):
    """Enum for training experience levels."""
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class OnboardingCompleteRequest(BaseModel):
    """Complete onboarding data request for saving to database."""
    # Personal info - REQUIRED
    age: int = Field(..., ge=13, le=120)
    gender: str = Field(..., description="male/female")
    height: float = Field(..., gt=0, description="Height in cm")
    weight: float = Field(..., gt=0, description="Weight in kg")
    body_fat_percentage: Optional[float] = Field(None, ge=0, le=100)

    # Activity and goals - REQUIRED
    activity_level: str = Field(..., description="sedentary/light/moderate/active/very_active")
    goal: str = Field(..., description="bulk/cut/maintain/recomp")

    # Training level - OPTIONAL (resistance training experience)
    training_level: Optional[str] = Field(None, description="beginner/intermediate/advanced")

    # User experience - REQUIRED (at least one item each)
    pain_points: List[str] = Field(..., min_items=1, description="User pain points")
    dietary_preferences: List[str] = Field(..., min_items=1, description="Dietary preferences")

    # Meal preferences - REQUIRED
    meals_per_day: int = Field(..., ge=1, le=10)