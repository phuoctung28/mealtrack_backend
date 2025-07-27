"""
Daily nutrition summary response DTO.
"""
from typing import Dict

from pydantic import BaseModel, Field


# TODO (tony): remove fiber field
class MacrosResponse(BaseModel):
    """Macronutrient response model."""
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams") 
    fat: float = Field(..., description="Fat in grams")
    fiber: float = Field(0.0, description="Fiber in grams")

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