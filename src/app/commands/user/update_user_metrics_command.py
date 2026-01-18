"""
Command to update user metrics (weight, activity level, body fat).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateUserMetricsCommand:
    """Update user metrics (including fitness goal) and trigger TDEE recalculation."""
    user_id: str
    weight_kg: Optional[float] = None
    activity_level: Optional[str] = None
    body_fat_percent: Optional[float] = None
    fitness_goal: Optional[str] = None

