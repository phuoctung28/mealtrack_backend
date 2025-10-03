"""
TDEE calculation request DTOs.
"""
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, root_validator


class SexEnum(str, Enum):
    """Enum for biological sex."""
    male = "male"
    female = "female"


class ActivityLevelEnum(str, Enum):
    """Enum for activity levels."""
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    extra = "extra"


class GoalEnum(str, Enum):
    """Enum for fitness goals."""
    maintenance = "maintenance"
    cutting = "cutting"
    bulking = "bulking"


class UnitSystemEnum(str, Enum):
    """Enum for unit systems."""
    metric = "metric"
    imperial = "imperial"


class TdeeCalculationRequest(BaseModel):
    """Request DTO for TDEE calculation matching Flutter OnboardingData."""
    age: int = Field(..., ge=13, le=120, description="User age")
    sex: SexEnum = Field(..., description="User biological sex")
    height: float = Field(..., gt=0, description="Height in user's preferred units")
    weight: float = Field(..., gt=0, description="Weight in user's preferred units")
    body_fat_percentage: Optional[float] = Field(
        None, 
        ge=5, 
        le=55, 
        description="Body fat percentage (optional)"
    )
    activity_level: ActivityLevelEnum = Field(..., description="Activity level")
    goal: GoalEnum = Field(..., description="Fitness goal")
    unit_system: UnitSystemEnum = Field(
        UnitSystemEnum.metric, 
        description="Unit system for height/weight"
    )

    @root_validator(skip_on_failure=True)
    def validate_measurements_with_units(cls, values):
        """Validate height and weight based on unit system."""
        unit_system = values.get('unit_system')
        height = values.get('height')
        weight = values.get('weight')
        
        if height is not None and unit_system is not None:
            if unit_system == UnitSystemEnum.metric:
                if not (100 <= height <= 272):
                    raise ValueError('Height must be between 100-272 cm for metric system')
            else:  # imperial
                if not (39 <= height <= 107):
                    raise ValueError('Height must be between 39-107 inches for imperial system')
        
        if weight is not None and unit_system is not None:
            if unit_system == UnitSystemEnum.metric:
                if not (30 <= weight <= 250):
                    raise ValueError('Weight must be between 30-250 kg for metric system')
            else:  # imperial
                if not (66 <= weight <= 551):
                    raise ValueError('Weight must be between 66-551 lbs for imperial system')
        
        return values
    
    class Config:
        json_schema_extra = {
            "example": {
                "age": 25,
                "sex": "male",
                "height": 180.0,
                "weight": 75.0,
                "body_fat_percentage": 15.0,
                "activity_level": "moderate",
                "goal": "maintenance",
                "unit_system": "metric"
            }
        }


class BatchTdeeCalculationRequest(BaseModel):
    """Request DTO for batch TDEE calculations."""
    calculations: List[TdeeCalculationRequest] = Field(
        ..., 
        min_items=1,
        max_items=10,
        description="List of TDEE calculations to perform"
    )