from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class OnboardingResponseRequest(BaseModel):
    section_id: str = Field(..., description="ID of the onboarding section")
    field_responses: Dict[str, Any] = Field(..., description="Mapping of field_id to response value")

class OnboardingCompleteRequest(BaseModel):
    """Complete onboarding data request for saving to database."""
    # Personal info
    age: int = Field(..., ge=13, le=120)
    gender: str = Field(..., description="male/female/other")
    height: float = Field(..., gt=0, description="Height in cm")
    weight: float = Field(..., gt=0, description="Weight in kg")
    body_fat_percentage: Optional[float] = Field(None, ge=0, le=100)
    
    # Activity and goals
    activity_level: str = Field(..., description="sedentary/light/moderate/active/extra")
    goal: str = Field(..., description="maintenance/cutting/bulking")
    target_weight: Optional[float] = Field(None, gt=0)
    
    # Preferences
    dietary_preferences: Optional[List[str]] = []
    health_conditions: Optional[List[str]] = []
    allergies: Optional[List[str]] = []
    
    # Meal preferences
    meals_per_day: Optional[int] = Field(3, ge=1, le=10)
    snacks_per_day: Optional[int] = Field(1, ge=0, le=10)