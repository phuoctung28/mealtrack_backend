from typing import Optional, List, Dict, Any, Union

from pydantic import BaseModel


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

class OnboardingResponseResponse(BaseModel):
    response_id: str
    user_id: Optional[str] = None
    section_id: str
    field_responses: Dict[str, Any]
    completed_at: Optional[str] = None
    created_at: Optional[str] = None


class OnboardingResponse(BaseModel):
    """Response for successful onboarding data save."""
    message: str
    user_id: str
    profile_id: str
    tdee_calculation: Dict[str, Any]