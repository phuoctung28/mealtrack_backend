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

    # User experience
    pain_points: List[str] = Field(default_factory=list, description="User pain points")
    dietary_preferences: List[str] = Field(default_factory=list, description="Dietary preferences")

    # Meal preferences - OPTIONAL (default 3, screen removed in onboarding redesign)
    meals_per_day: int = Field(3, ge=1, le=10)

    # Target weight - OPTIONAL
    target_weight_kg: Optional[float] = Field(None, gt=0)

    # Attribution - OPTIONAL (screen removed in onboarding redesign)
    referral_sources: List[str] = Field(default_factory=list, description="How user heard about us")

    # Onboarding redesign fields (NM-44)
    challenge_duration: Optional[str] = Field(None, description="e.g. '30_days', '60_days', '90_days'")
    training_types: Optional[List[str]] = Field(None, description="e.g. ['strength', 'cardio', 'yoga']")

    # Custom macro overrides (optional, set during onboarding)
    custom_protein_g: Optional[float] = Field(None, gt=0, description="Custom protein target in grams")
    custom_carbs_g: Optional[float] = Field(None, gt=0, description="Custom carbs target in grams")
    custom_fat_g: Optional[float] = Field(None, gt=0, description="Custom fat target in grams")