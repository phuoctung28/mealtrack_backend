"""
Authentication-related enums for API schemas.
"""
from enum import Enum


class AuthProviderEnum(str, Enum):
    """Authentication provider enumeration."""
    PHONE = "phone"
    GOOGLE = "google"
    
    @classmethod
    def from_string(cls, value: str) -> 'AuthProviderEnum':
        """Convert string to AuthProviderEnum with validation."""
        try:
            return cls(value.lower())
        except ValueError:
            # Default to email for unknown providers
            return cls.PHONE