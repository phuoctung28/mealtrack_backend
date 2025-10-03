"""
User management response schemas for Firebase integration.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from ..common.auth_enums import AuthProviderEnum


class UserProfileResponse(BaseModel):
    """Response containing user profile information."""
    id: str = Field(..., description="User internal ID")
    firebase_uid: str = Field(..., description="Firebase user unique identifier")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    phone_number: Optional[str] = Field(None, description="Phone number")
    display_name: Optional[str] = Field(None, description="Display name")
    photo_url: Optional[str] = Field(None, description="Profile photo URL")
    provider: AuthProviderEnum = Field(..., description="Authentication provider")
    is_active: bool = Field(..., description="Whether user account is active")
    onboarding_completed: bool = Field(..., description="Whether user completed onboarding")
    last_accessed: Optional[datetime] = Field(None, description="Last accessed timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserSyncResponse(BaseModel):
    """Response from user sync operation."""
    user: UserProfileResponse = Field(..., description="User profile data")
    created: bool = Field(..., description="Whether user was newly created")
    updated: bool = Field(..., description="Whether existing user was updated")
    message: str = Field(..., description="Operation result message")


class UserStatusResponse(BaseModel):
    """Response containing user status information."""
    firebase_uid: str = Field(..., description="Firebase user unique identifier")
    onboarding_completed: bool = Field(..., description="Whether user completed onboarding")
    is_active: bool = Field(..., description="Whether user account is active")
    last_accessed: Optional[datetime] = Field(None, description="Last accessed timestamp")


class UserUpdateResponse(BaseModel):
    """Response from user update operations."""
    firebase_uid: str = Field(..., description="Firebase user unique identifier")
    updated: bool = Field(..., description="Whether update was successful")
    message: str = Field(..., description="Operation result message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")


class OnboardingCompletionResponse(BaseModel):
    """Response from onboarding completion operation."""
    firebase_uid: str = Field(..., description="Firebase user unique identifier")
    onboarding_completed: bool = Field(..., description="Current onboarding completion status")
    updated: bool = Field(..., description="Whether update was successful")
    message: str = Field(..., description="Operation result message")