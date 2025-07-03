from typing import Optional, List, Dict, Any, Union

from pydantic import BaseModel, Field


class OnboardingFieldResponse(BaseModel):
    field_id: str
    label: str
    field_type: str
    required: bool
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    validation: Optional[Dict[str, Any]] = None
    default_value: Optional[Union[str, int, float, bool]] = None

class OnboardingSectionResponse(BaseModel):
    section_id: str
    title: str
    description: str
    section_type: str
    order: int
    fields: List[OnboardingFieldResponse]
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class OnboardingSectionsResponse(BaseModel):
    sections: List[OnboardingSectionResponse]
    total_sections: int

class OnboardingResponseRequest(BaseModel):
    section_id: str = Field(..., description="ID of the onboarding section")
    field_responses: Dict[str, Any] = Field(..., description="Mapping of field_id to response value")

class OnboardingResponseResponse(BaseModel):
    response_id: str
    user_id: Optional[str] = None
    section_id: str
    field_responses: Dict[str, Any]
    completed_at: Optional[str] = None
    created_at: Optional[str] = None

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