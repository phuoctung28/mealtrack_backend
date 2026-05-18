"""Command to log a workout session."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.model.workout.workout_log import Intensity, WorkoutType


@dataclass
class LogWorkoutCommand:
    user_id: str
    workout_type: WorkoutType
    intensity: Intensity
    duration_minutes: int
    logged_at: datetime
    notes: Optional[str] = None
