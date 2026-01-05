from enum import Enum

from pydantic import BaseModel, Field


class GoalEnum(str, Enum):
    cut = "cut"
    bulk = "bulk"
    recomp = "recomp"


class UpdateFitnessGoalRequest(BaseModel):
    goal: GoalEnum = Field(..., description="New fitness goal")
    override: bool = Field(False, description="Allow bypassing cooldown guardrail")


class UpdateMetricsRequest(BaseModel):
    """Unified update for weight, activity level, body fat, and fitness goal."""
    weight_kg: float | None = Field(None, description="Weight in kg", gt=0)
    activity_level: str | None = Field(None, description="Activity level")
    body_fat_percent: float | None = Field(None, description="Body fat percentage", ge=0, le=70)
    fitness_goal: GoalEnum | None = Field(None, description="Fitness goal (cut, bulk, recomp)")
    override: bool = Field(False, description="Allow bypassing goal cooldown guardrail")


