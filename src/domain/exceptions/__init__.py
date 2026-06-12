"""Domain exception classes."""

from src.domain.exceptions.base import (
    AuthenticationException,
    AuthorizationException,
    BusinessLogicException,
    ConflictException,
    ExternalServiceException,
    MealTrackException,
    ResourceNotFoundException,
    ValidationException,
)

__all__ = [
    "MealTrackException",
    "ValidationException",
    "ResourceNotFoundException",
    "BusinessLogicException",
    "ConflictException",
    "ExternalServiceException",
    "AuthenticationException",
    "AuthorizationException",
]
