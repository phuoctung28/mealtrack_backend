"""
Pydantic response schemas for progress screen endpoints.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class StreakResponse(BaseModel):
    """Response for GET /v1/meals/streak."""

    current_streak: int
    best_streak: int
    last_logged_date: Optional[str] = None  # YYYY-MM-DD, None if never logged
    scan_count: int = 0  # total meals created via scanner


class DailyBreakdownEntry(BaseModel):
    """Macros consumed vs target for a single day."""

    date: str  # YYYY-MM-DD
    calories_consumed: float
    calories_target: float
    protein_consumed: float
    protein_target: float
    carbs_consumed: float
    carbs_target: float
    fat_consumed: float
    fat_target: float
    meal_count: int


class DailyBreakdownResponse(BaseModel):
    """Response for GET /v1/meals/weekly/daily-breakdown."""

    days: List[DailyBreakdownEntry]
    week_start: str  # YYYY-MM-DD (Monday)
