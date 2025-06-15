"""
Base HTTP DTOs for API layer.

This module contains ONLY pure HTTP request/response DTOs with no business logic.
Application-specific models with business logic have been moved to app/models/.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


# Import application models for reference


# ============================================================================
# HTTP Base DTO Classes (Pure API Contract)
# ============================================================================

class BaseRequest(BaseModel):
    """Base class for all HTTP request DTOs."""
    
    class Config:
        """Pydantic configuration for HTTP requests."""
        str_strip_whitespace = True
        validate_assignment = True


class BaseResponse(BaseModel):
    """Base class for all HTTP response DTOs."""
    
    class Config:
        """Pydantic configuration for HTTP responses."""
        from_attributes = True


class TimestampedResponse(BaseResponse):
    """Base HTTP response with common timestamp fields."""
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============================================================================
# Simple HTTP DTOs (No Business Logic)
# ============================================================================

class ImageSchema(BaseModel):
    """Simple image data DTO for HTTP responses."""
    image_id: str
    format: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    url: Optional[str] = None


class MetadataSchema(BaseModel):
    """Generic metadata DTO for API responses."""
    endpoint_version: str
    scalable_design: bool = True
    supported_types: List[str]
    future_types: Optional[List[str]] = None
    enrichment_level: Optional[str] = None


# ============================================================================
# HTTP Error DTOs
# ============================================================================

class ErrorResponse(BaseResponse):
    """Standard error response DTO."""
    error: str
    message: str
    details: Optional[dict] = None
    status_code: int


class ValidationErrorResponse(BaseResponse):
    """Validation error response DTO."""
    error: str = "validation_error"
    message: str
    field_errors: List[dict]


# Note: MacrosSchema, NutritionSummarySchema, PaginationMetadata, and StatusSchema
# have been moved to app/models/ as they contain business logic.
# They are imported above for backward compatibility in DTOs. 