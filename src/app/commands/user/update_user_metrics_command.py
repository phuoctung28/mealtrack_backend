"""
Command to update user metrics (weight, job type, training, body fat).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateUserMetricsCommand:
    """Update user metrics (including fitness goal) and trigger TDEE recalculation."""
    user_id: str
    weight_kg: Optional[float] = None
    job_type: Optional[str] = None
    training_days_per_week: Optional[int] = None
    training_minutes_per_session: Optional[int] = None
    body_fat_percent: Optional[float] = None
    fitness_goal: Optional[str] = None
    training_level: Optional[str] = None
    target_weight_kg: Optional[float] = None

