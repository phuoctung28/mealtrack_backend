from enum import Enum

from pydantic import BaseModel, Field


class GoalEnum(str, Enum):
    cut = "cut"
    bulk = "bulk"
    recomp = "recomp"


class TrainingLevelEnum(str, Enum):
    """Enum for training experience levels."""
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class UpdateFitnessGoalRequest(BaseModel):
    goal: GoalEnum = Field(..., description="New fitness goal")


class UpdateMetricsRequest(BaseModel):
    """Unified update for weight, activity level, body fat, and fitness goal."""
    weight_kg: float | None = Field(None, description="Weight in kg", gt=0)
    activity_level: str | None = Field(None, description="Activity level")
    body_fat_percent: float | None = Field(None, description="Body fat percentage", ge=0, le=70)
    fitness_goal: GoalEnum | None = Field(None, description="Fitness goal (cut, bulk, recomp)")
    training_level: TrainingLevelEnum | None = Field(None, description="Training level (beginner, intermediate, advanced)")


