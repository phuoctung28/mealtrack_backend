"""
Onboarding DTOs (Data Transfer Objects) for user onboarding APIs.

This module contains:
- Onboarding field and section models
- Request DTOs for onboarding responses
- Response DTOs for onboarding data
"""

from typing import Optional, List, Dict, Any, Union

from pydantic import Field

from .base import BaseRequest, BaseResponse, TimestampedResponse


# ============================================================================
# Onboarding Data Models
# ============================================================================

class OnboardingFieldResponse(BaseResponse):
    """Response model for onboarding field definition."""
    field_id: str
    label: str
    field_type: str
    required: bool
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    validation: Optional[Dict[str, Any]] = None
    default_value: Optional[Union[str, int, float, bool]] = None


class OnboardingSectionResponse(TimestampedResponse):
    """Response model for onboarding section definition."""
    section_id: str
    title: str
    description: str
    section_type: str
    order: int
    fields: List[OnboardingFieldResponse]
    is_active: bool


# ============================================================================
# Request DTOs
# ============================================================================

class OnboardingResponseRequest(BaseRequest):
    """DTO for submitting onboarding responses."""
    section_id: str = Field(..., description="ID of the onboarding section")
    field_responses: Dict[str, Any] = Field(..., description="Mapping of field_id to response value")


# ============================================================================
# Response DTOs
# ============================================================================

class OnboardingSectionsResponse(BaseResponse):
    """Collection of onboarding sections."""
    sections: List[OnboardingSectionResponse]
    total_sections: int


class OnboardingResponseResponse(TimestampedResponse):
    """Response for onboarding submission."""
    response_id: str
    user_id: Optional[str] = None
    section_id: str
    field_responses: Dict[str, Any]
    completed_at: Optional[str] = None 