"""Hydration request schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class LogHydrationRequest(BaseModel):
    """Request to log a hydration entry."""

    drink_id: str = Field(..., description="Drink ID from catalog (hydration category)")
    volume_ml: int = Field(..., gt=0, le=2000, description="Volume in ml (1–2000)")
    target_date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")


class LogCaloricDrinkRequest(BaseModel):
    """Request to log a caloric drink entry."""

    drink_id: str = Field(..., description="Drink ID from catalog (caloric category)")
    volume_ml: int = Field(..., gt=0, le=2000, description="Volume in ml (1–2000)")
    target_date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
