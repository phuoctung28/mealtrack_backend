"""
Activity DTOs (Data Transfer Objects) for activity tracking APIs.

This module contains:
- Activity data models
- Activity response DTOs
- Activity enrichment schemas
"""

from typing import Optional, List

from pydantic import Field

from app.models import MacrosSchema, PaginationMetadata
from .base import BaseResponse, ImageSchema


# ============================================================================
# Activity Data Models
# ============================================================================

class ActivityEnrichedData(BaseResponse):
    """Enriched nutrition data for activities."""
    meal_name: str
    total_calories: float = Field(..., ge=0)
    weight_grams: float = Field(..., gt=0)
    calories_per_100g: float = Field(..., ge=0) 
    macros: MacrosSchema
    confidence_score: float = Field(..., ge=0, le=1)
    food_items_count: int = Field(..., ge=0)


# ============================================================================
# Activity Response DTOs
# ============================================================================

class ActivityResponse(BaseResponse):
    """Single activity response DTO."""
    activity_id: str
    activity_type: str
    meal_id: str
    status: str
    title: str
    description: str
    created_at: Optional[str] = None
    ready_at: Optional[str] = None
    enriched_data: Optional[ActivityEnrichedData] = None
    image: Optional[ImageSchema] = None
    error_message: Optional[str] = None



class ActivitiesResponse(BaseResponse):
    """Complete activities response with pagination."""
    activities: List[ActivityResponse]
    pagination: PaginationMetadata