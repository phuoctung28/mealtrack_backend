"""
Command to sync user data from Firebase authentication.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from src.api.schemas.common.auth_enums import AuthProviderEnum


@dataclass
class SyncUserCommand:
    """Command to sync user data from Firebase authentication."""
    firebase_uid: str
    email: str
    phone_number: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    provider: AuthProviderEnum = AuthProviderEnum.PHONE
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@dataclass
class UpdateUserLastAccessedCommand:
    """Command to update user's last accessed timestamp."""
    firebase_uid: str
    last_accessed: Optional[datetime] = None