"""
User management request schemas for Firebase integration.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from ..common.auth_enums import AuthProviderEnum


class UserSyncRequest(BaseModel):
    """Request to sync user data from Firebase authentication."""
    firebase_uid: str = Field(..., description="Firebase user unique identifier")
    email: EmailStr = Field(..., description="User email address")
    phone_number: Optional[str] = Field(None, description="User phone number (E.164 format)")
    display_name: Optional[str] = Field(None, description="User display name from Firebase")
    photo_url: Optional[str] = Field(None, description="User profile photo URL")
    provider: AuthProviderEnum = Field(..., description="Authentication provider (phone, google)")
    
    # Generated/computed fields
    username: Optional[str] = Field(None, description="Generated username (auto-generated if not provided)")
    first_name: Optional[str] = Field(None, description="First name (extracted from display_name if not provided)")
    last_name: Optional[str] = Field(None, description="Last name (extracted from display_name if not provided)")


class UserUpdateLastAccessedRequest(BaseModel):
    """Request to update user's last accessed timestamp."""
    firebase_uid: str = Field(..., description="Firebase user unique identifier")
    last_accessed: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Last accessed timestamp")


class UserCreateRequest(BaseModel):
    """Request to create a new user (legacy support)."""
    firebase_uid: str = Field(..., description="Firebase user unique identifier")
    email: EmailStr = Field(..., description="User email address")
    username: Optional[str] = Field(None, description="Username (auto-generated if not provided)")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    phone_number: Optional[str] = Field(None, description="Phone number")
    display_name: Optional[str] = Field(None, description="Display name")
    photo_url: Optional[str] = Field(None, description="Profile photo URL")
    provider: AuthProviderEnum = Field(default=AuthProviderEnum.PHONE, description="Authentication provider")