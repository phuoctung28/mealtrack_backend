"""Command to delete a workout log entry."""

from dataclasses import dataclass


@dataclass
class DeleteWorkoutCommand:
    workout_log_id: str
    user_id: str  # Required for ownership verification
