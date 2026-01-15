"""
MealService - Domain service for meal operations.
Provides shared meal editing and management logic.
"""
import logging
from typing import List, Optional
from uuid import uuid4

from src.domain.model.meal.food_item_change import FoodItemChange, CustomNutritionData
from src.domain.model.meal import Meal
from src.domain.model.nutrition import FoodItem
from src.domain.model.nutrition import Nutrition
from src.domain.ports.meal_repository_port import MealRepositoryPort

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
        # Ensure meal.nutrition exists and food_items list is initialized
        if meal.nutrition is None:
            from src.domain.model.nutrition.macros import Macros
            meal.nutrition = Nutrition(
                calories=0.0,
                macros=Macros(protein=0.0, carbs=0.0, fat=0.0),
                food_items=[]
            )
        
        # Ensure food_items list exists
        if meal.nutrition.food_items is None:
            meal.nutrition.food_items = []
        
        for change in food_item_changes:
            if change.action == "add":
                # Add new food item
                from src.domain.model.nutrition.macros import Macros
                
                # Calculate calories and macros from custom_nutrition if provided
                if change.custom_nutrition:
                    scale_factor = change.quantity / 100.0  # Custom nutrition is per 100g
                    calories = change.custom_nutrition.calories_per_100g * scale_factor
                    macros = Macros(
                        protein=change.custom_nutrition.protein_per_100g * scale_factor,
                        carbs=change.custom_nutrition.carbs_per_100g * scale_factor,
                        fat=change.custom_nutrition.fat_per_100g * scale_factor
                    )
                else:
                    # Default values when no custom nutrition provided
                    calories = 0.0
                    macros = Macros(protein=0.0, carbs=0.0, fat=0.0)
                
                new_food_item = FoodItem(
                    id=str(uuid4()),
                    name=change.name,
                    quantity=change.quantity,
                    unit=change.unit,
                    calories=calories,
                    macros=macros,
                    is_custom=change.custom_nutrition is not None
                )
                meal.nutrition.food_items.append(new_food_item)
                logger.info(f"Added food item: {change.name}")
            
            elif change.action == "remove":
                # Remove food item
                if change.id:
                    meal.nutrition.food_items = [
                        item for item in meal.nutrition.food_items
                        if item.id != change.id
                    ]
                    logger.info(f"Removed food item: {change.id}")
                else:
                    logger.warning("Remove action requires food item id")
            
            elif change.action == "update":
                # Update existing food item
                from src.domain.model.nutrition.macros import Macros
                
                if not change.id:
                    logger.warning("Update action requires food item id")
                    continue
                
                for item in meal.nutrition.food_items:
                    if item.id == change.id:
                        if change.name is not None:
                            item.name = change.name
                        if change.quantity is not None:
                            item.quantity = change.quantity
                        if change.unit is not None:
                            item.unit = change.unit
                        if change.custom_nutrition is not None:
                            # Recalculate calories and macros from custom nutrition
                            scale_factor = (change.quantity or item.quantity) / 100.0
                            item.calories = change.custom_nutrition.calories_per_100g * scale_factor
                            item.macros = Macros(
                                protein=change.custom_nutrition.protein_per_100g * scale_factor,
                                carbs=change.custom_nutrition.carbs_per_100g * scale_factor,
                                fat=change.custom_nutrition.fat_per_100g * scale_factor
                            )
                            item.is_custom = True
                        logger.info(f"Updated food item: {change.id}")
                        break
        
        # Recalculate total nutrition from food items
        from src.domain.services import NutritionCalculationService
        nutrition_service = NutritionCalculationService()
        meal.nutrition = nutrition_service.calculate_meal_total(meal.nutrition.food_items)
        
        return meal
    
    def add_custom_ingredient(
        self,
        meal_id: str,
        name: str,
        quantity: float,
        unit: str,
        nutrition: Optional[CustomNutritionData] = None
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
            custom_nutrition=nutrition
        )
        
        updated_meal = self.apply_food_item_changes(meal, [food_item_change])
        return self.meal_repository.save(updated_meal)