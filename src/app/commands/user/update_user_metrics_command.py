"""
Command to update user metrics (weight, activity level, body fat).
"""
from dataclasses import dataclass


@dataclass
class UpdateUserMetricsCommand:
    """Update user metrics (including fitness goal) and trigger TDEE recalculation."""
    user_id: str
    weight_kg: float | None = None
    activity_level: str | None = None
    body_fat_percent: float | None = None
    fitness_goal: str | None = None

