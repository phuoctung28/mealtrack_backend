"""API HTTP exception mapping — domain → FastAPI HTTPException.

Domain exception classes live in src.domain.exceptions.base.
This module owns only the HTTP status mapping and logging.
Re-exports the domain classes so existing api-layer callers don't break.
"""

import logging
import traceback

from fastapi import HTTPException, status

from src.domain.exceptions.ai_exceptions import AIUnavailableError
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

logger = logging.getLogger(__name__)

# Re-export so existing `from src.api.exceptions import X` in the API layer continues
# to work without changes.
__all__ = [
    "MealTrackException",
    "ValidationException",
    "ResourceNotFoundException",
    "BusinessLogicException",
    "ConflictException",
    "ExternalServiceException",
    "AuthenticationException",
    "AuthorizationException",
    "create_http_exception",
    "handle_exception",
]

_STATUS_MAP: dict[type, int] = {
    ValidationException: status.HTTP_400_BAD_REQUEST,
    ResourceNotFoundException: status.HTTP_404_NOT_FOUND,
    BusinessLogicException: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ExternalServiceException: status.HTTP_503_SERVICE_UNAVAILABLE,
    AuthenticationException: status.HTTP_401_UNAUTHORIZED,
    AuthorizationException: status.HTTP_403_FORBIDDEN,
    ConflictException: status.HTTP_409_CONFLICT,
}


def create_http_exception(exc: MealTrackException) -> HTTPException:
    """Convert a domain exception to an HTTPException with the correct status code."""
    status_code = _STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


def handle_exception(exc: Exception) -> HTTPException:
    """Convert any exception to an HTTPException for consistent API responses."""

    if isinstance(exc, AIUnavailableError):
        logger.warning(
            "AI provider unavailable: %s",
            exc,
            extra={
                "error_code": "AI_UNAVAILABLE",
                "attempted_models": exc.attempted_models,
                "last_error": exc.last_error,
            },
        )
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "AI_UNAVAILABLE",
                "message": "AI meal generation is temporarily unavailable",
                "details": {"attempted_models": exc.attempted_models},
            },
        )

    if isinstance(exc, MealTrackException):
        logger.warning(
            "MealTrack exception occurred: %s - %s",
            exc.error_code,
            exc.message,
            extra={"error_code": exc.error_code, "details": exc.details},
        )
        return create_http_exception(exc)

    if isinstance(exc, HTTPException):
        logger.warning("HTTP exception occurred: %s - %s", exc.status_code, exc.detail)
        return exc

    logger.error(
        "Unexpected exception occurred: %s - %s",
        type(exc).__name__,
        str(exc),
        exc_info=True,
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "stack_trace": traceback.format_exc(),
        },
    )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
        },
    )
