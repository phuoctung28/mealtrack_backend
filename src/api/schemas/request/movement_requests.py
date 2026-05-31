"""Movement request schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class LogMovementRequest(BaseModel):
    activity_id: Optional[str] = Field(None, max_length=64)
    activity_name: str = Field(..., min_length=1, max_length=100)
    duration_min: int = Field(..., ge=1, le=600)
    kcal_burned: float = Field(..., ge=0)
    intensity: str
    include_in_balance: bool
    target_date: Optional[str] = None
