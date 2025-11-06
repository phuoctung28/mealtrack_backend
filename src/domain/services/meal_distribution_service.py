"""
Domain service for calculating calorie distribution across meals.
"""
from typing import List

from src.domain.model.meal_planning import CalorieDistribution, UserNutritionTargets
from src.domain.model.meal_planning import MealType


class MealDistributionService:
    """Service for calculating calorie distribution across meal types."""
    
    # Standard distribution ratios
    BREAKFAST_RATIO = 0.25
    LUNCH_RATIO = 0.35
    DINNER_RATIO = 0.40
    SNACK_RATIO = 0.10
    
    def calculate_distribution(
        self, 
        meal_types: List[MealType], 
        nutrition_targets: UserNutritionTargets
    ) -> CalorieDistribution:
        """Calculate calorie distribution for given meal types."""
        target_calories = nutrition_targets.calories
        
        num_snacks = sum(1 for mt in meal_types if mt == MealType.SNACK)
        
        # Reserve calories for snacks
        snack_calories_per_snack = int(target_calories * self.SNACK_RATIO) if num_snacks > 0 else 0
        remaining_calories = target_calories - (num_snacks * snack_calories_per_snack)
        
        distribution = {}
        
        for meal_type in meal_types:
            if meal_type == MealType.SNACK:
                distribution[meal_type] = snack_calories_per_snack
            elif meal_type == MealType.BREAKFAST:
                distribution[meal_type] = int(remaining_calories * self.BREAKFAST_RATIO)
            elif meal_type == MealType.LUNCH:
                distribution[meal_type] = int(remaining_calories * self.LUNCH_RATIO)
            elif meal_type == MealType.DINNER:
                distribution[meal_type] = int(remaining_calories * self.DINNER_RATIO)
            else:
                # Default for any other meal types
                distribution[meal_type] = int(remaining_calories / 3)
        
        return CalorieDistribution(distribution)