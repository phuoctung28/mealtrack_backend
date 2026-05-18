"""Workout-related request DTOs."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.domain.model.workout.workout_log import Intensity, WorkoutType


class LogWorkoutRequest(BaseModel):
    """Request body for POST /v1/workouts/log."""

    workout_type: WorkoutType = Field(..., description="Workout category")
    intensity: Intensity = Field(..., description="Workout intensity level")
    duration_minutes: int = Field(
        ..., gt=0, le=600, description="Duration in minutes (1–600)"
    )
    logged_at: datetime = Field(
        ..., description="When the workout occurred (ISO 8601, tz-aware)"
    )
    notes: Optional[str] = Field(
        None, max_length=500, description="Optional free-text notes"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "workout_type": "RUNNING",
                "intensity": "MODERATE",
                "duration_minutes": 45,
                "logged_at": "2026-05-18T07:30:00+07:00",
                "notes": "Morning run in the park",
            }
        }
    }
