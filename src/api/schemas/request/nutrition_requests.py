"""
Nutrition API request schemas.
"""
from datetime import date

from pydantic import BaseModel, Field


class BulkNutritionRequest(BaseModel):
    """Request for bulk nutrition data (query params)."""
    start: date = Field(..., description="Start date (inclusive)")
    end: date = Field(..., description="End date (inclusive)")
