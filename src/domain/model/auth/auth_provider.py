"""
Authentication provider domain model.
"""
from enum import Enum


class AuthProvider(str, Enum):
    """Authentication provider enumeration."""
    GOOGLE = "google"
    APPLE = "apple"
    
    @classmethod
    def from_string(cls, value: str) -> 'AuthProvider':
        """Convert string to AuthProvider with validation."""
        try:
            return cls(value.lower())
        except ValueError:
            # Default to google for unknown providers
            return cls.GOOGLE


# Backward compatibility alias
AuthProviderEnum = AuthProvider