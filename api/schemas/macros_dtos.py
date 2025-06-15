"""
Macros DTOs (Data Transfer Objects) for nutrition tracking APIs.

This module contains pure HTTP DTOs for nutrition tracking endpoints.
Business logic models have been moved to app/models/nutrition.py.
"""

from typing import Optional, Dict, List

from pydantic import Field, validator

from app.models import MacrosSchema
from .base import BaseRequest, BaseResponse


# ============================================================================
# Request DTOs
# ============================================================================

class OnboardingChoicesRequest(BaseRequest):
    """HTTP DTO for user onboarding nutrition setup - pure data transfer."""
    age: int = Field(..., ge=13, le=120, description="User age")
    gender: str = Field(..., description="User gender (male/female/other)")
    height: float = Field(..., gt=0, description="Height in cm")
    weight: float = Field(..., gt=0, description="Weight in kg")
    activity_level: str = Field(..., description="Activity level")
    goal: str = Field(..., description="Fitness goal")
    goal_weight: Optional[float] = Field(None, gt=0, description="Target weight in kg")
    dietary_preferences: Optional[List[str]] = Field(None, description="Dietary preferences/restrictions")
    health_conditions: Optional[List[str]] = Field(None, description="Health conditions")
    timeline_months: Optional[int] = Field(6, ge=1, le=24, description="Timeline to achieve goal in months")


class ConsumedMacrosRequest(BaseRequest):
    """DTO for tracking consumed meals."""
    meal_id: str = Field(..., description="ID of the consumed meal")
    weight_grams: Optional[float] = Field(None, gt=0, description="Actual weight consumed in grams")
    portion_percentage: Optional[float] = Field(None, gt=0, le=100, description="Percentage of the meal consumed")
    
    @validator('portion_percentage')
    def validate_portion(cls, v):
        if v is not None and (v <= 0 or v > 100):
            raise ValueError('Portion percentage must be between 0 and 100')
        return v


# ============================================================================
# Response DTOs
# ============================================================================

class MacrosCalculationResponse(BaseResponse):
    """Response for calculated user macros and targets."""
    target_calories: float
    target_macros: MacrosSchema
    estimated_timeline_months: int
    bmr: float = Field(..., description="Basal Metabolic Rate")
    tdee: float = Field(..., description="Total Daily Energy Expenditure")
    daily_calorie_deficit_surplus: float = Field(..., description="Daily calorie adjustment needed")
    recommendations: List[str] = Field(..., description="Personalized recommendations")
    user_macros_id: str = Field(..., description="ID for tracking daily macros")


class UpdatedMacrosResponse(BaseResponse):
    """Response after updating consumed macros."""
    user_macros_id: str
    target_date: str
    target_calories: float
    target_macros: MacrosSchema
    consumed_calories: float
    consumed_macros: MacrosSchema
    remaining_calories: float
    remaining_macros: MacrosSchema
    completion_percentage: Dict[str, float]
    is_goal_met: bool = Field(..., description="Whether daily goals are met")
    recommendations: List[str] = Field(..., description="Recommendations based on current consumption")


class DailyMacrosResponse(BaseResponse):
    """Response for daily macros summary."""
    date: str
    target_calories: float
    target_macros: MacrosSchema
    consumed_calories: float
    consumed_macros: MacrosSchema
    remaining_calories: float
    remaining_macros: MacrosSchema
    completion_percentage: Dict[str, float] 