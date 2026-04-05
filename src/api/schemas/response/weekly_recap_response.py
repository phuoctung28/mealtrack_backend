"""
Weekly recap response schema.
"""
from typing import List, Optional

from pydantic import BaseModel


class DailyBreakdownItem(BaseModel):
    """Per-day macro breakdown entry."""

    date: str
    calories_consumed: float
    calories_target: float
    protein_consumed: float
    protein_target: float
    carbs_consumed: float
    carbs_target: float
    fat_consumed: float
    fat_target: float
    meal_count: int


class WeeklyRecapResponse(BaseModel):
    """Response schema for weekly performance recap."""

    week_start_date: str
    week_end_date: str
    week_number: int
    is_first_week: bool
    days_tracked: int
    days_in_week: int = 7

    # Totals consumed
    total_calories_consumed: float
    total_protein_consumed: float
    total_carbs_consumed: float
    total_fat_consumed: float

    # Weekly targets
    total_calories_target: float
    total_protein_target: float
    total_carbs_target: float
    total_fat_target: float

    # Adherence — NOT capped at 100; mobile handles overconsumption display
    calorie_adherence_pct: float
    protein_adherence_pct: float

    # Averages per tracked day (NOT per 7 days)
    avg_daily_calories: float
    avg_daily_protein: float

    cheat_day_count: int

    # Last meal date across any week, used by mobile for gap detection
    last_activity_date: Optional[str]

    daily_breakdown: List[DailyBreakdownItem]
