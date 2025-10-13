"""
API Exception classes for consistent error handling.
"""
import logging
import traceback
from typing import Optional, Dict, Any

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class MealTrackException(Exception):
    """Base exception for all MealTrack exceptions."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
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


def create_http_exception(exc: MealTrackException) -> HTTPException:
    """Convert domain exception to HTTP exception with appropriate status code."""
    
    status_map = {
        ValidationException: status.HTTP_400_BAD_REQUEST,
        ResourceNotFoundException: status.HTTP_404_NOT_FOUND,
        BusinessLogicException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ExternalServiceException: status.HTTP_503_SERVICE_UNAVAILABLE,
        AuthenticationException: status.HTTP_401_UNAUTHORIZED,
        AuthorizationException: status.HTTP_403_FORBIDDEN,
        ConflictException: status.HTTP_409_CONFLICT,
    }
    
    status_code = status_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


def handle_exception(exc: Exception) -> HTTPException:
    """Handle any exception and convert to appropriate HTTP exception."""
    
    if isinstance(exc, MealTrackException):
        logger.warning(
            f"MealTrack exception occurred: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "details": exc.details
            }
        )
        return create_http_exception(exc)
    
    if isinstance(exc, HTTPException):
        logger.warning(
            f"HTTP exception occurred: {exc.status_code} - {exc.detail}"
        )
        return exc
    
    # Unexpected exceptions - log full stack trace
    logger.error(
        f"Unexpected exception occurred: {type(exc).__name__} - {str(exc)}",
        exc_info=True,
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "stack_trace": traceback.format_exc()
        }
    )
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {"error": str(exc)}
        }
    )