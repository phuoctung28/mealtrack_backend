from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from .meal_schemas import MacrosSchema

class OnboardingChoicesRequest(BaseModel):
    age: int = Field(..., ge=13, le=120, description="User age")
    gender: str = Field(..., description="User gender (male/female/other)")
    height: float = Field(..., gt=0, description="Height in cm")
    weight: float = Field(..., gt=0, description="Weight in kg")
    activity_level: str = Field(..., description="Activity level (sedentary/lightly_active/moderately_active/very_active/extra_active)")
    goal: str = Field(..., description="Fitness goal (lose_weight/maintain_weight/gain_weight/build_muscle)")
    goal_weight: Optional[float] = Field(None, gt=0, description="Target weight in kg")
    dietary_preferences: Optional[List[str]] = Field(None, description="Dietary preferences/restrictions")
    health_conditions: Optional[List[str]] = Field(None, description="Health conditions")
    timeline_months: Optional[int] = Field(6, ge=1, le=24, description="Timeline to achieve goal in months")

    @validator('gender')
    def validate_gender(cls, v):
        allowed = ['male', 'female', 'other']
        if v.lower() not in allowed:
            raise ValueError(f'Gender must be one of: {allowed}')
        return v.lower()

    @validator('activity_level')
    def validate_activity_level(cls, v):
        allowed = ['sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extra_active']
        if v.lower() not in allowed:
            raise ValueError(f'Activity level must be one of: {allowed}')
        return v.lower()

    @validator('goal')
    def validate_goal(cls, v):
        allowed = ['lose_weight', 'maintain_weight', 'gain_weight', 'build_muscle']
        if v.lower() not in allowed:
            raise ValueError(f'Goal must be one of: {allowed}')
        return v.lower()

class MacrosCalculationResponse(BaseModel):
    target_calories: float
    target_macros: MacrosSchema
    estimated_timeline_months: int
    bmr: float = Field(..., description="Basal Metabolic Rate")
    tdee: float = Field(..., description="Total Daily Energy Expenditure")
    daily_calorie_deficit_surplus: float = Field(..., description="Daily calorie adjustment needed")
    recommendations: List[str] = Field(..., description="Personalized recommendations")
    user_macros_id: str = Field(..., description="ID for tracking daily macros")

class ConsumedMacrosRequest(BaseModel):
    calories: float = Field(..., ge=0, description="Consumed calories")
    macros: MacrosSchema = Field(..., description="Consumed macros")
    meal_id: Optional[str] = Field(None, description="Related meal ID if from a meal")
    food_id: Optional[str] = Field(None, description="Related food ID if from manual food entry")

class UpdatedMacrosResponse(BaseModel):
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

class DailyMacrosResponse(BaseModel):
    date: str
    target_calories: float
    target_macros: MacrosSchema
    consumed_calories: float
    consumed_macros: MacrosSchema
    remaining_calories: float
    remaining_macros: MacrosSchema
    completion_percentage: Dict[str, float] 