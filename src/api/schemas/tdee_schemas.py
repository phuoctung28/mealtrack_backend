from typing import Optional
from pydantic import BaseModel, Field, validator, root_validator

from src.domain.model import Goal


class TdeeCalculationRequest(BaseModel):
    """Request schema for TDEE calculation matching Flutter OnboardingData."""
    age: int = Field(..., ge=13, le=120, description="User age")
    sex: str = Field(..., description="User sex (male|female)")
    height: float = Field(..., gt=0, description="Height in user's preferred units")
    weight: float = Field(..., gt=0, description="Weight in user's preferred units")
    body_fat_percentage: Optional[float] = Field(None, ge=5, le=55, description="Body fat percentage (optional)")
    activity_level: str = Field(..., description="Activity level (sedentary|light|moderate|active|extra)")
    goal: str = Field(..., description="Goal (maintenance|cutting|bulking)")
    unit_system: str = Field("metric", description="Unit system (metric|imperial)")

    @validator('sex')
    def validate_sex(cls, v):
        allowed = ['male', 'female']
        if v.lower() not in allowed:
            raise ValueError(f'Sex must be one of: {allowed}')
        return v.lower()

    @validator('activity_level')
    def validate_activity_level(cls, v):
        allowed = ['sedentary', 'light', 'moderate', 'active', 'extra']
        if v.lower() not in allowed:
            raise ValueError(f'Activity level must be one of: {allowed}')
        return v.lower()

    @validator('goal')
    def validate_goal(cls, v):
        allowed = ['maintenance', 'cutting', 'bulking']
        if v.lower() not in allowed:
            raise ValueError(f'Goal must be one of: {allowed}')
        return v.lower()

    @validator('unit_system')
    def validate_unit_system(cls, v):
        allowed = ['metric', 'imperial']
        if v.lower() not in allowed:
            raise ValueError(f'Unit system must be one of: {allowed}')
        return v.lower()

    @root_validator(skip_on_failure=True)
    def validate_measurements_with_units(cls, values):
        """Validate height and weight based on unit system."""
        unit_system = values.get('unit_system', 'metric')
        height = values.get('height')
        weight = values.get('weight')
        
        if height is not None:
            if unit_system == 'metric':
                if not (100 <= height <= 272):
                    raise ValueError('Height must be between 100-272 cm for metric system')
            else:  # imperial
                if not (39 <= height <= 107):
                    raise ValueError('Height must be between 39-107 inches for imperial system')
        
        if weight is not None:
            if unit_system == 'metric':
                if not (30 <= weight <= 250):
                    raise ValueError('Weight must be between 30-250 kg for metric system')
            else:  # imperial
                if not (66 <= weight <= 551):
                    raise ValueError('Weight must be between 66-551 lbs for imperial system')
        
        return values


class MacroTargetsResponse(BaseModel):
    """Macro targets for a specific goal matching Flutter MacroTargets."""
    calories: float = Field(..., description="Calories per day")
    protein: float = Field(..., description="Protein in grams per day")
    fat: float = Field(..., description="Fat in grams per day")
    carbs: float = Field(..., description="Carbohydrates in grams per day")


class TdeeCalculationResponse(BaseModel):
    """Response schema for TDEE calculation matching Flutter TdeeResult."""
    bmr: float = Field(..., description="Basal Metabolic Rate")
    tdee: float = Field(..., description="Total Daily Energy Expenditure")
    macros: MacroTargetsResponse = Field(..., description="Macro targets")
    goal: Goal = Field(..., description="Goal (maintenance|cutting|bulking)")
