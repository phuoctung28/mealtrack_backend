"""Domain-owned exception hierarchy for MealTrack.

These exceptions carry no HTTP semantics. HTTP status mapping lives in
src/api/exceptions.py via create_http_exception().
"""

from typing import Any


class MealTrackException(Exception):
    """Base exception for all MealTrack exceptions."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(MealTrackException):
    """Raised when request validation fails."""

    pass


class ResourceNotFoundException(MealTrackException):
    """Raised when a requested resource is not found."""

    pass


class BusinessLogicException(MealTrackException):
    """Raised when business rules are violated."""

    pass


class ConflictException(MealTrackException):
    """Raised when a request conflicts with current resource state (e.g., cooldown)."""

    pass


class ExternalServiceException(MealTrackException):
    """Raised when an external service fails."""

    pass


class AuthenticationException(MealTrackException):
    """Raised when authentication fails."""

    pass


class AuthorizationException(MealTrackException):
    """Raised when user lacks permission."""

    pass
