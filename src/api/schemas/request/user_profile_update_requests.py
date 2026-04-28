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


class JobTypeEnum(str, Enum):
    """Enum for job types based on daily movement requirements."""

    desk = "desk"
    on_feet = "on_feet"
    physical = "physical"


class UpdateFitnessGoalRequest(BaseModel):
    goal: GoalEnum = Field(..., description="New fitness goal")


class UpdateMetricsRequest(BaseModel):
    """Unified update for weight, job type, training, body fat, and fitness goal."""

    weight_kg: float | None = Field(None, description="Weight in kg", gt=0)
    job_type: str | None = Field(None, description="Job type (desk, on_feet, physical)")
    training_days_per_week: int | None = Field(
        None, ge=0, le=7, description="Training days per week"
    )
    training_minutes_per_session: int | None = Field(
        None, ge=15, le=180, description="Minutes per training session"
    )
    body_fat_percent: float | None = Field(
        None, description="Body fat percentage", ge=0, le=70
    )
    fitness_goal: GoalEnum | None = Field(
        None, description="Fitness goal (cut, bulk, recomp)"
    )
    training_level: TrainingLevelEnum | None = Field(
        None, description="Training level (beginner, intermediate, advanced)"
    )
