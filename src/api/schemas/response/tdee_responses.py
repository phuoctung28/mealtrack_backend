"""
TDEE calculation response DTOs.
"""


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
                "carbs": 300.0,
            }
        }


class TdeeCalculationResponse(BaseModel):
    """Response DTO for TDEE calculation matching Flutter TdeeResult."""

    bmr: float = Field(..., gt=0, description="Basal Metabolic Rate")
    tdee: float = Field(..., gt=0, description="Total Daily Energy Expenditure")
    macros: MacroTargetsResponse = Field(..., description="Macro targets for the goal")
    goal: GoalEnum = Field(..., description="Goal used for calculation")

    calculation_contract: str | None = Field(
        None,
        description="Versioned calculation policy used to produce this response",
    )

    # Additional useful information
    activity_multiplier: float | None = Field(
        None, description="Activity level multiplier used"
    )
    formula_used: str | None = Field(
        None, description="Formula used (Mifflin-St Jeor or Katch-McArdle)"
    )
    is_custom: bool = Field(
        False,
        description="True when macros are user-customized (not algorithm-calculated)",
    )
    macro_preset: str | None = Field(
        None, description="Resolved backend macro policy (standard or keto)"
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
                    "carbs": 294.0,
                },
                "goal": "recomp",
                "activity_multiplier": 1.4,
                "formula_used": "Mifflin-St Jeor",
            }
        }


class BatchTdeeCalculationResponse(BaseModel):
    """Response DTO for batch TDEE calculations."""

    results: list[TdeeCalculationResponse] = Field(
        ..., description="List of TDEE calculation results"
    )
    total_calculations: int = Field(
        ..., ge=0, description="Total calculations performed"
    )


class TdeeComparisonResponse(BaseModel):
    """Response DTO for comparing TDEE calculations."""

    current: TdeeCalculationResponse = Field(
        ..., description="Current TDEE calculation"
    )
    previous: TdeeCalculationResponse | None = Field(
        None, description="Previous TDEE calculation for comparison"
    )
    changes: dict | None = Field(None, description="Changes between calculations")


class TdeeHistoryResponse(BaseModel):
    """Response DTO for TDEE calculation history."""

    user_id: str = Field(..., description="User ID")
    calculations: list[dict] = Field(..., description="List of historical calculations")
    total_count: int = Field(..., ge=0, description="Total number of calculations")


class TdeeErrorResponse(BaseModel):
    """Response DTO for TDEE calculation errors."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    field: str | None = Field(None, description="Field that caused the error")
