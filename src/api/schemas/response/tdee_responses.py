"""
TDEE calculation response DTOs.
"""
from typing import Optional, List, Dict

from pydantic import BaseModel, Field

from src.api.schemas.request.tdee_requests import GoalEnum


class MacroTargetsResponse(BaseModel):
    """Response DTO for macro targets matching Flutter MacroTargets."""
    calories: float = Field(..., ge=0, description="Daily calorie target")
    protein: float = Field(..., ge=0, description="Protein in grams per day")
    fat: float = Field(..., ge=0, description="Fat in grams per day")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams per day")
    
    class Config:
        json_schema_extra = {
            "example": {
                "calories": 2500.0,
                "protein": 125.0,
                "fat": 83.3,
                "carbs": 300.0
            }
        }


class TdeeCalculationResponse(BaseModel):
    """Response DTO for TDEE calculation matching Flutter TdeeResult."""
    bmr: float = Field(..., gt=0, description="Basal Metabolic Rate")
    tdee: float = Field(..., gt=0, description="Total Daily Energy Expenditure")
    macros: MacroTargetsResponse = Field(..., description="Macro targets for the goal")
    goal: GoalEnum = Field(..., description="Goal used for calculation")
    
    # Additional useful information
    activity_multiplier: Optional[float] = Field(
        None, 
        description="Activity level multiplier used"
    )
    formula_used: Optional[str] = Field(
        None, 
        description="Formula used (Mifflin-St Jeor or Katch-McArdle)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "bmr": 1750.0,
                "tdee": 2450.0,
                "macros": {
                    "calories": 2450.0,
                    "protein": 122.5,
                    "fat": 81.7,
                    "carbs": 294.0
                },
                "goal": "recomp",
                "activity_multiplier": 1.4,
                "formula_used": "Mifflin-St Jeor"
            }
        }


class BatchTdeeCalculationResponse(BaseModel):
    """Response DTO for batch TDEE calculations."""
    results: List[TdeeCalculationResponse] = Field(
        ..., 
        description="List of TDEE calculation results"
    )
    total_calculations: int = Field(..., ge=0, description="Total calculations performed")


class TdeeComparisonResponse(BaseModel):
    """Response DTO for comparing TDEE calculations."""
    current: TdeeCalculationResponse = Field(..., description="Current TDEE calculation")
    previous: Optional[TdeeCalculationResponse] = Field(
        None, 
        description="Previous TDEE calculation for comparison"
    )
    changes: Optional[Dict] = Field(
        None,
        description="Changes between calculations"
    )


class TdeeHistoryResponse(BaseModel):
    """Response DTO for TDEE calculation history."""
    user_id: str = Field(..., description="User ID")
    calculations: List[Dict] = Field(..., description="List of historical calculations")
    total_count: int = Field(..., ge=0, description="Total number of calculations")


class TdeeErrorResponse(BaseModel):
    """Response DTO for TDEE calculation errors."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")