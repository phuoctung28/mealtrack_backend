"""
Authentication provider domain model.
"""

from enum import StrEnum


class AuthProvider(StrEnum):
    """Authentication provider enumeration."""

    GOOGLE = "google"
    APPLE = "apple"
    EMAIL_LINK = "email_link"
    ANONYMOUS = "anonymous"

    @classmethod
    def from_string(cls, value: str) -> "AuthProvider":
        """Convert string to AuthProvider with validation."""
        try:
            return cls(value.lower())
        except ValueError:
            # Default to google for unknown providers
            return cls.GOOGLE


# Backward compatibility alias
AuthProviderEnum = AuthProvider
