"""
Nutrition API response schemas.
"""
from typing import Dict, Optional

from pydantic import BaseModel, Field


class MacroTotals(BaseModel):
    """Macronutrient totals."""
    calories: float = Field(..., description="Total calories")
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")


class DateTotals(BaseModel):
    """Consumed, target, and remaining totals for a date."""
    consumed: MacroTotals
    target: MacroTotals
    remaining: MacroTotals


class DateSummary(BaseModel):
    """Summary for a single date."""
    has_meals: bool = Field(..., description="Whether the date has any meals logged")
    meal_count: int = Field(..., description="Number of meals on this date")
    totals: DateTotals


class WeeklyBudgetSummary(BaseModel):
    """Weekly budget summary included in bulk response."""
    week_start_date: str = Field(..., description="Week start date in YYYY-MM-DD")
    target_calories: float = Field(..., description="Weekly target calories")
    consumed_calories: float = Field(..., description="Consumed calories so far")
    remaining_calories: float = Field(..., description="Remaining calories")
    adjusted_daily_calories: float = Field(..., description="Adjusted daily target")
    remaining_days: int = Field(..., description="Days remaining in the week")


class BulkNutritionResponse(BaseModel):
    """Response for bulk nutrition endpoint."""
    dates: Dict[str, DateSummary] = Field(..., description="Date-indexed nutrition summaries")
    weekly_budget: Optional[WeeklyBudgetSummary] = Field(None, description="Current week's budget")
    cache_version: str = Field(..., description="Cache version for staleness detection")
