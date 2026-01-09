"""
Authentication-related enums for API schemas.
DEPRECATED: Import from src.domain.model.auth instead.
"""
# Re-export from domain for backward compatibility
from src.domain.model.auth import AuthProviderEnum

__all__ = ["AuthProviderEnum"]