from typing import List, Dict

from pydantic import BaseModel, Field

from .meal_responses import MacrosResponse


class MacrosCalculationResponse(BaseModel):
    target_calories: float
    target_macros: MacrosResponse
    estimated_timeline_months: int
    bmr: float = Field(..., description="Basal Metabolic Rate")
    tdee: float = Field(..., description="Total Daily Energy Expenditure")
    daily_calorie_deficit_surplus: float = Field(..., description="Daily calorie adjustment needed")
    recommendations: List[str] = Field(..., description="Personalized recommendations")
    user_macros_id: str = Field(..., description="ID for tracking daily macros")

class UpdatedMacrosResponse(BaseModel):
    user_macros_id: str
    target_date: str
    target_calories: float
    target_macros: MacrosResponse
    consumed_calories: float
    consumed_macros: MacrosResponse
    remaining_calories: float
    remaining_macros: MacrosResponse
    completion_percentage: Dict[str, float]
    is_goal_met: bool = Field(..., description="Whether daily goals are met")
    recommendations: List[str] = Field(..., description="Recommendations based on current consumption")

class DailyMacrosResponse(BaseModel):
    date: str
    target_calories: float
    target_macros: MacrosResponse
    consumed_calories: float
    consumed_macros: MacrosResponse
    remaining_calories: float
    remaining_macros: MacrosResponse
    completion_percentage: Dict[str, float]