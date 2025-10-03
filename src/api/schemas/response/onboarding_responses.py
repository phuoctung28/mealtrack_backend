from typing import Dict, Any

from pydantic import BaseModel


class OnboardingResponse(BaseModel):
    """Response for successful onboarding data save."""
    message: str
    user_id: str
    profile_id: str
    tdee_calculation: Dict[str, Any]