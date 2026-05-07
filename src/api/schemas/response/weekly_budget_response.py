"""
Weekly budget response schema.
"""

from typing import List, Optional

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
    cheat_days: List[str] = []

    # Phase 2: Skip & Redistribute
    skipped_days: int = 0
    show_logging_prompt: bool = False

    # Phase 3: Tomorrow preview (null when on-track)
    preview_tomorrow_calories: Optional[float] = None
    preview_tomorrow_protein: Optional[float] = None
    preview_tomorrow_carbs: Optional[float] = None
    preview_tomorrow_fat: Optional[float] = None
    preview_direction: Optional[str] = None  # "over" | "under"
    preview_delta: Optional[int] = None
    preview_today_delta: Optional[int] = None
