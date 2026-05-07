"""
Command to mark a meal as INACTIVE (soft delete).
"""

from dataclasses import dataclass


@dataclass
class DeleteMealCommand:
    meal_id: str
    user_id: str  # Required for ownership verification
