"""Response schemas for retention campaign endpoints."""

from datetime import datetime

from pydantic import BaseModel


class MobilityIntentResponse(BaseModel):
    success: bool


class AssetSummaryResponse(BaseModel):
    meal_scan_count: int
    hydration_entry_count: int
    hydration_win_count: int
    movement_entry_count: int
    active_day_count: int
    trial_end_at: datetime | None
    lock_at: datetime | None
