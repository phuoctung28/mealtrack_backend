"""
Daily nutrition summary response DTO.
"""
from typing import Dict, Optional

from pydantic import BaseModel, Field


class MacrosResponse(BaseModel):
    """Macronutrient response model."""
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")


class WeeklyContextResponse(BaseModel):
    """Weekly budget context for daily response."""
    adjusted_target_calories: float = Field(..., description="Adjusted daily calories based on weekly budget")
    adjusted_target_carbs: float = Field(..., description="Adjusted daily carbs based on weekly budget")
    adjusted_target_fat: float = Field(..., description="Adjusted daily fat based on weekly budget")
    daily_protein: float = Field(..., description="Daily protein target (fixed)")
    bmr_floor_active: bool = Field(..., description="True if adjusted target hit BMR floor")
    remaining_days: int = Field(..., description="Days remaining in the week")
    cheat_slots_remaining: int = Field(..., description="Cheat meal slots remaining this week")


class CheatTagSuggestion(BaseModel):
    """Smart prompt suggestion for cheat tagging."""
    meal_id: str = Field(..., description="Meal ID to suggest tagging")
    reason: str = Field(..., description="Reason for suggestion")


class DailyNutritionResponse(BaseModel):
    """Response DTO for daily nutrition summary - matches Flutter frontend expectations."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    target_calories: float = Field(..., description="Target calories for the day")
    target_macros: MacrosResponse = Field(..., description="Target macros for the day")
    consumed_calories: float = Field(..., description="Calories consumed so far")
    consumed_macros: MacrosResponse = Field(..., description="Macros consumed so far")
    remaining_calories: float = Field(..., description="Remaining calories for the day")
    remaining_macros: MacrosResponse = Field(..., description="Remaining macros for the day")
    completion_percentage: Dict[str, float] = Field(..., description="Completion percentage for calories and macros")
    weekly_context: Optional[WeeklyContextResponse] = Field(None, description="Weekly budget context")
    suggest_cheat_tag: Optional[CheatTagSuggestion] = Field(None, description="Smart prompt suggestion")