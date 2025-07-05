"""
Daily nutrition summary response DTO.
"""
from typing import Dict

from pydantic import BaseModel, Field


class DailyNutritionResponse(BaseModel):
    """Response DTO for daily nutrition summary."""
    date: str = Field(..., description="Date in ISO format")
    total_meals: int = Field(..., ge=0, description="Total number of meals")
    totals: Dict[str, float] = Field(..., description="Total nutrition values")