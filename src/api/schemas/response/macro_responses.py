"""
Response schemas for macro tracking endpoints.
"""
from typing import Dict, List

from pydantic import BaseModel, Field

from .daily_nutrition_response import MacrosResponse


class UpdatedMacrosResponse(BaseModel):
    """Response model for consumed macros tracking."""
    user_macros_id: str = Field(..., description="ID of the user's daily macros record")
    target_date: str = Field(..., description="Target date in YYYY-MM-DD format")
    target_calories: float = Field(..., description="Target calories for the day")
    target_macros: MacrosResponse = Field(..., description="Target macros for the day")
    consumed_calories: float = Field(..., description="Calories consumed so far")
    consumed_macros: MacrosResponse = Field(..., description="Macros consumed so far")
    remaining_calories: float = Field(..., description="Remaining calories for the day")
    remaining_macros: MacrosResponse = Field(..., description="Remaining macros for the day")
    completion_percentage: Dict[str, float] = Field(..., description="Completion percentage for calories and macros")
    is_goal_met: bool = Field(..., description="Whether daily goal has been met")
    recommendations: List[str] = Field(default_factory=list, description="Nutrition recommendations")


class MacrosCalculationResponse(BaseModel):
    """Response model for macro calculation from onboarding."""
    target_calories: float = Field(..., description="Calculated target calories")
    target_macros: MacrosResponse = Field(..., description="Calculated target macros")
    estimated_timeline_months: int = Field(..., description="Estimated timeline to reach goal")
    bmr: float = Field(..., description="Basal Metabolic Rate")
    tdee: float = Field(..., description="Total Daily Energy Expenditure")
    daily_calorie_deficit_surplus: float = Field(..., description="Daily calorie deficit/surplus")
    recommendations: List[str] = Field(default_factory=list, description="Personalized recommendations")
    user_macros_id: str = Field(..., description="ID of created user macros record")


class MealMacrosResponse(BaseModel):
    """Response model for meal-specific macros."""
    meal_id: str = Field(..., description="ID of the meal")
    name: str = Field(..., description="Name of the meal")
    total_calories: float = Field(..., description="Total calories in the meal")
    total_weight_grams: float = Field(..., description="Total weight of the meal in grams")
    calories_per_100g: float = Field(..., description="Calories per 100g")
    macros_per_100g: MacrosResponse = Field(..., description="Macros per 100g")
    total_macros: MacrosResponse = Field(..., description="Total macros in the meal")
    actual_weight_grams: float = Field(None, description="Actual weight consumed in grams")
    actual_calories: float = Field(None, description="Actual calories consumed")
    actual_macros: MacrosResponse = Field(None, description="Actual macros consumed")