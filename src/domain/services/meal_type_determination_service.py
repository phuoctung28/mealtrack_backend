"""
Domain service for determining required meal types based on user preferences.
"""
from datetime import datetime
from typing import List

from src.domain.model.meal_planning import MealType


def determine_meal_type_from_timestamp(created_at: datetime) -> str:
    """Determine meal type based on creation timestamp hour.

    Hour ranges:
    - Breakfast: 5:00 - 10:59
    - Lunch: 11:00 - 15:59
    - Dinner: 16:00 - 21:59
    - Snack: All other times
    """
    hour = created_at.hour

    if 5 <= hour < 11:
        return "breakfast"
    elif 11 <= hour < 16:
        return "lunch"
    elif 16 <= hour < 22:
        return "dinner"
    else:
        return "snack"


class MealTypeDeterminationService:
    """Service for determining what meal types to generate."""

    def determine_meal_types(self, meals_per_day: int, include_snacks: bool) -> List[MealType]:
        """Determine what meal types to generate based on user preferences."""
        meal_types = [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER]

        # Add additional meals if requested (beyond standard 3)
        if meals_per_day > 3:
            additional_meals = meals_per_day - 3
            for _ in range(additional_meals):
                meal_types.append(MealType.SNACK)

        # Add snacks if specifically requested and not already included
        if include_snacks and MealType.SNACK not in meal_types:
            meal_types.append(MealType.SNACK)

        return meal_types