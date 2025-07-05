"""
Calculate TDEE command.
"""
from dataclasses import dataclass
from typing import Optional

from src.app.events.base import Command


@dataclass
class CalculateTdeeCommand(Command):
    """Command to calculate TDEE."""
    age: int
    sex: str  # 'male' or 'female'
    height_cm: float
    weight_kg: float
    activity_level: str
    goal: str
    body_fat_percentage: Optional[float] = None
    unit_system: str = "metric"