from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class TrainingLevelEnum(str, Enum):
    """Enum for training experience levels."""
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class JobTypeEnum(str, Enum):
    """Enum for job types based on daily movement requirements."""
    desk = "desk"
    on_feet = "on_feet"
    physical = "physical"


class OnboardingCompleteRequest(BaseModel):
    """Complete onboarding data request for saving to database."""
    # Personal info - REQUIRED (DOB replaces age — age computed server-side)
    birth_year: int = Field(..., ge=1900, le=2100)
    birth_month: int = Field(..., ge=1, le=12)
    birth_day: int = Field(..., ge=1, le=31)
    gender: str = Field(..., description="male/female")
    height: float = Field(..., gt=0, description="Height in cm")
    weight: float = Field(..., gt=0, description="Weight in kg")
    body_fat_percentage: Optional[float] = Field(None, ge=0, le=100)

    # Activity and goals - REQUIRED
    job_type: str = Field(..., description="desk/on_feet/physical")
    training_days_per_week: int = Field(..., ge=0, le=7, description="Days of training per week")
    training_minutes_per_session: int = Field(..., ge=15, le=180, description="Minutes per training session")
    goal: str = Field(..., description="bulk/cut/maintain/recomp")

    # Training level - OPTIONAL (resistance training experience)
    training_level: Optional[str] = Field(None, description="beginner/intermediate/advanced")

    # User experience - REQUIRED (at least one item each)
    pain_points: List[str] = Field(..., min_items=1, description="User pain points")
    dietary_preferences: List[str] = Field(..., min_items=1, description="Dietary preferences")

    # Meal preferences - REQUIRED
    meals_per_day: int = Field(..., ge=1, le=10)

    # Target weight - OPTIONAL
    target_weight_kg: Optional[float] = Field(None, gt=0)

    # Attribution - REQUIRED (multi-select, min 1 item)
    referral_sources: List[str] = Field(..., min_items=1, description="How user heard about us")