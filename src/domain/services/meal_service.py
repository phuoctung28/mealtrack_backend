"""
MealService - Domain service for meal operations.
Provides shared meal editing and management logic.
"""
import logging
from typing import List, Optional
from uuid import uuid4

from src.domain.model.meal import Meal
from src.domain.model.nutrition import FoodItem
from src.domain.model.nutrition import Nutrition
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.app.commands.meal.edit_meal_command import FoodItemChange


logger = logging.getLogger(__name__)


class MealService:
    """Service for meal operations."""
    
    def __init__(self, meal_repository: MealRepositoryPort):
        self.meal_repository = meal_repository
    
    def apply_food_item_changes(
        self,
        meal: Meal,
        food_item_changes: List[FoodItemChange]
    ) -> Meal:
        """Apply food item changes to a meal."""
        for change in food_item_changes:
            if change.action == "add":
                # Add new food item
                new_food_item = FoodItem(
                    id=str(uuid4()),
                    name=change.name,
                    quantity=change.quantity,
                    unit=change.unit,
                    nutrition=change.custom_nutrition if change.custom_nutrition else Nutrition()
                )
                meal.food_items.append(new_food_item)
                logger.info(f"Added food item: {change.name}")
            
            elif change.action == "remove":
                # Remove food item
                meal.food_items = [
                    item for item in meal.food_items
                    if item.id != change.food_item_id
                ]
                logger.info(f"Removed food item: {change.food_item_id}")
            
            elif change.action == "update":
                # Update existing food item
                for item in meal.food_items:
                    if item.id == change.food_item_id:
                        if change.name is not None:
                            item.name = change.name
                        if change.quantity is not None:
                            item.quantity = change.quantity
                        if change.unit is not None:
                            item.unit = change.unit
                        if change.custom_nutrition is not None:
                            item.nutrition = change.custom_nutrition
                        logger.info(f"Updated food item: {change.food_item_id}")
                        break
        
        # Recalculate total nutrition
        meal.recalculate_nutrition()
        return meal
    
    def add_custom_ingredient(
        self,
        meal_id: str,
        name: str,
        quantity: float,
        unit: str,
        nutrition: Optional[Nutrition] = None
    ) -> Meal:
        """Add a custom ingredient to a meal."""
        meal = self.meal_repository.find_by_id(meal_id)
        if not meal:
            raise ValueError(f"Meal {meal_id} not found")
        
        food_item_change = FoodItemChange(
            action="add",
            name=name,
            quantity=quantity,
            unit=unit,
            custom_nutrition=nutrition if nutrition else Nutrition()
        )
        
        updated_meal = self.apply_food_item_changes(meal, [food_item_change])
        return self.meal_repository.save(updated_meal)