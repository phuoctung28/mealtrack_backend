"""
Domain service for determining required meal types based on user preferences.
"""
from typing import List

from src.domain.model.meal_plan import MealType


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