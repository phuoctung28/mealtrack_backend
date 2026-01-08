"""
Core meal service combining meal operations and meal type determination.
Consolidates meal_service.py and meal_type_determination_service.py.
"""
import logging
from datetime import datetime, time
from typing import Optional, List, Dict, Any

from src.domain.model.meal import Meal
from src.domain.model.nutrition import FoodItem, Nutrition, Macros
from src.domain.model.meal_planning import MealType

logger = logging.getLogger(__name__)


class MealCoreService:
    """
    Core domain service for meal operations.
    
    Responsibilities:
    - Apply food item changes to meals
    - Recalculate nutrition
    - Determine meal type from time
    """

    # Meal type time boundaries
    BREAKFAST_START = time(5, 0)
    BREAKFAST_END = time(10, 30)
    LUNCH_START = time(11, 0)
    LUNCH_END = time(14, 30)
    DINNER_START = time(17, 0)
    DINNER_END = time(21, 0)
    
    # Default calorie distributions by meal type
    DEFAULT_DISTRIBUTIONS = {
        MealType.BREAKFAST: 0.25,
        MealType.LUNCH: 0.35,
        MealType.DINNER: 0.30,
        MealType.SNACK: 0.10,
    }

    def apply_food_item_changes(
        self,
        meal: Meal,
        updated_items: List[FoodItem],
        removed_item_ids: List[str],
    ) -> Meal:
        """
        Apply food item changes to a meal.
        
        Args:
            meal: The meal to update
            updated_items: List of food items to add/update
            removed_item_ids: List of item IDs to remove
            
        Returns:
            Updated meal with recalculated nutrition
        """
        # Remove items
        meal.food_items = [
            item for item in meal.food_items 
            if item.id not in removed_item_ids
        ]
        
        # Update or add items
        existing_ids = {item.id for item in meal.food_items}
        for updated_item in updated_items:
            if updated_item.id in existing_ids:
                # Update existing
                for i, item in enumerate(meal.food_items):
                    if item.id == updated_item.id:
                        meal.food_items[i] = updated_item
                        break
            else:
                # Add new
                meal.food_items.append(updated_item)
        
        # Recalculate nutrition
        meal.nutrition = self.calculate_nutrition(meal.food_items)
        
        return meal

    def calculate_nutrition(self, food_items: List[FoodItem]) -> Nutrition:
        """
        Calculate total nutrition from food items.
        
        Args:
            food_items: List of food items
            
        Returns:
            Aggregated nutrition data
        """
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        
        for item in food_items:
            total_calories += item.calories or 0
            total_protein += item.macros.protein or 0
            total_carbs += item.macros.carbs or 0
            total_fat += item.macros.fat or 0
        
        return Nutrition(
            calories=round(total_calories, 1),
            macros=Macros(
                protein=round(total_protein, 1),
                carbs=round(total_carbs, 1),
                fat=round(total_fat, 1),
            ),
            food_items=food_items,
        )

    def determine_meal_type(
        self,
        meal_time: Optional[datetime] = None,
    ) -> MealType:
        """
        Determine meal type based on time of day.
        
        Args:
            meal_time: Datetime of the meal (defaults to now)
            
        Returns:
            Appropriate MealType enum
        """
        if meal_time is None:
            meal_time = datetime.now()
        
        t = meal_time.time()
        
        if self.BREAKFAST_START <= t <= self.BREAKFAST_END:
            return MealType.BREAKFAST
        elif self.LUNCH_START <= t <= self.LUNCH_END:
            return MealType.LUNCH
        elif self.DINNER_START <= t <= self.DINNER_END:
            return MealType.DINNER
        else:
            return MealType.SNACK

    def get_calorie_target_for_meal(
        self,
        meal_type: MealType,
        daily_calories: int,
        custom_distribution: Optional[Dict[MealType, float]] = None,
    ) -> int:
        """
        Get calorie target for a specific meal type.
        
        Args:
            meal_type: Type of meal
            daily_calories: Total daily calorie target
            custom_distribution: Optional custom distribution percentages
            
        Returns:
            Calorie target for the meal
        """
        distribution = custom_distribution or self.DEFAULT_DISTRIBUTIONS
        percentage = distribution.get(meal_type, 0.25)
        return int(daily_calories * percentage)

    def validate_meal(self, meal: Meal) -> List[str]:
        """
        Validate a meal for completeness.
        
        Args:
            meal: Meal to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not meal.name or not meal.name.strip():
            errors.append("Meal name is required")
        
        if not meal.food_items:
            errors.append("Meal must have at least one food item")
        
        if meal.nutrition:
            if meal.nutrition.calories < 0:
                errors.append("Calories cannot be negative")
            if meal.nutrition.macros.protein < 0:
                errors.append("Protein cannot be negative")
        
        return errors
