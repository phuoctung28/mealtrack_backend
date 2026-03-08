"""
Weekly budget response schema.
"""
from typing import List

from pydantic import BaseModel


class WeeklyBudgetResponse(BaseModel):
    """Response schema for weekly macro budget."""

    week_start_date: str
    target_calories: float
    target_protein: float
    target_carbs: float
    target_fat: float
    consumed_calories: float
    consumed_protein: float
    consumed_carbs: float
    consumed_fat: float
    remaining_calories: float
    remaining_protein: float
    remaining_carbs: float
    remaining_fat: float
    adjusted_daily_calories: float
    adjusted_daily_carbs: float
    adjusted_daily_fat: float
    daily_protein: float
    remaining_days: int
    bmr_floor_active: bool
    cheat_days: List[str] = []  # List of "YYYY-MM-DD" date strings (manual marks only)
