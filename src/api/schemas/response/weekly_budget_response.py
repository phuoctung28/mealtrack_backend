"""
Weekly budget response schema.
"""
from pydantic import BaseModel
from typing import Optional


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
    cheat_slots_total: int
    cheat_slots_used: int
    cheat_slots_remaining: int
    adjusted_daily_calories: float
    adjusted_daily_carbs: float
    adjusted_daily_fat: float
    daily_protein: float
    remaining_days: int
    bmr_floor_active: bool


class CheatMealTagResponse(BaseModel):
    """Response schema for cheat meal tagging."""

    meal_id: str
    is_cheat_meal: bool
    cheat_slots_remaining: int
    message: str
