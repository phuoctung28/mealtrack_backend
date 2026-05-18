"""Workout CQRS commands."""

from .log_workout_command import LogWorkoutCommand
from .delete_workout_command import DeleteWorkoutCommand

__all__ = ["LogWorkoutCommand", "DeleteWorkoutCommand"]
