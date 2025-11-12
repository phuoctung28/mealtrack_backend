"""
Strategy pattern for handling different food item change actions.
Each strategy encapsulates the logic for add, update, or remove operations.
"""
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict

from src.app.commands.meal import FoodItemChange
from src.domain.model.nutrition import FoodItem
from src.domain.model.nutrition import Macros
from src.domain.services import NutritionCalculationService

logger = logging.getLogger(__name__)


class FoodItemChangeStrategy(ABC):
    """Base strategy for applying food item changes."""

    def __init__(self, nutrition_service: NutritionCalculationService):
        self.nutrition_service = nutrition_service

    @abstractmethod
    async def apply(
        self,
        food_items_dict: Dict[str, FoodItem],
        change: FoodItemChange
    ) -> None:
        """
        Apply the change to the food items dictionary.

        Args:
            food_items_dict: Dictionary of food items (id -> FoodItem)
            change: The change to apply
        """
        pass


class RemoveFoodItemStrategy(FoodItemChangeStrategy):
    """Strategy for removing a food item."""

    async def apply(
        self,
        food_items_dict: Dict[str, FoodItem],
        change: FoodItemChange
    ) -> None:
        """Remove food item from dictionary."""
        if not change.id:
            logger.warning("Remove action requires id")
            return

        food_items_dict.pop(change.id, None)
        logger.info(f"Removed food item: {change.id}")


class UpdateFoodItemStrategy(FoodItemChangeStrategy):
    """Strategy for updating an existing food item."""

    async def apply(
        self,
        food_items_dict: Dict[str, FoodItem],
        change: FoodItemChange
    ) -> None:
        """Update existing food item with new quantity/unit."""
        if not change.id or change.id not in food_items_dict:
            logger.warning(f"Update action requires valid id: {change.id}")
            return

        existing_item = food_items_dict[change.id]
        new_quantity = change.quantity or existing_item.quantity
        new_unit = change.unit or existing_item.unit

        # Check if unit changed - if so, fetch fresh nutrition data
        unit_changed = change.unit and change.unit != existing_item.unit

        if unit_changed:
            # Unit changed - fetch fresh nutrition data
            scaled_nutrition = self.nutrition_service.get_nutrition_for_ingredient(
                name=existing_item.name,
                quantity=new_quantity,
                unit=new_unit,
                fdc_id=existing_item.fdc_id
            )

            if scaled_nutrition:
                food_items_dict[change.id] = FoodItem(
                    id=existing_item.id,
                    name=existing_item.name,
                    quantity=new_quantity,
                    unit=new_unit,
                    calories=scaled_nutrition.calories,
                    macros=Macros(
                        protein=scaled_nutrition.protein,
                        carbs=scaled_nutrition.carbs,
                        fat=scaled_nutrition.fat
                    ),
                    micros=existing_item.micros,
                    confidence=0.9,
                    fdc_id=existing_item.fdc_id,
                    is_custom=existing_item.is_custom
                )
                logger.info(f"Updated food item with unit change: {existing_item.name}")
            else:
                # Fallback to simple scaling
                logger.warning(f"Could not fetch nutrition for unit change, using scaling")
                self._apply_simple_scaling(food_items_dict, change, existing_item, new_quantity, new_unit)
        else:
            # Same unit - just scale the nutrition
            self._apply_simple_scaling(food_items_dict, change, existing_item, new_quantity, new_unit)

    def _apply_simple_scaling(
        self,
        food_items_dict: Dict[str, FoodItem],
        change: FoodItemChange,
        existing_item: FoodItem,
        new_quantity: float,
        new_unit: str
    ) -> None:
        """Apply simple proportional scaling to nutrition."""
        scale_factor = new_quantity / existing_item.quantity

        food_items_dict[change.id] = FoodItem(
            id=existing_item.id,
            name=existing_item.name,
            quantity=new_quantity,
            unit=new_unit,
            calories=existing_item.calories * scale_factor,
            macros=Macros(
                protein=existing_item.macros.protein * scale_factor,
                carbs=existing_item.macros.carbs * scale_factor,
                fat=existing_item.macros.fat * scale_factor
            ),
            micros=existing_item.micros,
            confidence=existing_item.confidence,
            fdc_id=existing_item.fdc_id,
            is_custom=existing_item.is_custom
        )
        logger.info(f"Updated food item with scaling: {existing_item.name}")


class AddFoodItemStrategy(FoodItemChangeStrategy):
    """Strategy for adding a new food item."""

    def __init__(self, nutrition_service: NutritionCalculationService, food_service=None):
        super().__init__(nutrition_service)
        self.food_service = food_service

    async def apply(
        self,
        food_items_dict: Dict[str, FoodItem],
        change: FoodItemChange
    ) -> None:
        """Add new food item to dictionary."""
        new_item_id = str(uuid.uuid4())

        # Try to get nutrition from various sources
        quantity = change.quantity or 100
        unit = change.unit or "g"

        # Priority 1: Custom nutrition provided
        if change.custom_nutrition:
            food_item = self._create_from_custom_nutrition(
                new_item_id,
                change.name or "Custom Ingredient",
                quantity,
                unit,
                change.custom_nutrition
            )
            food_items_dict[new_item_id] = food_item
            logger.info(f"Added custom food item: {change.name}")
            return

        # Priority 2: Nutrition service (Pinecone/USDA)
        if change.name:
            scaled_nutrition = self.nutrition_service.get_nutrition_for_ingredient(
                name=change.name,
                quantity=quantity,
                unit=unit,
                fdc_id=change.fdc_id
            )

            if scaled_nutrition:
                food_items_dict[new_item_id] = FoodItem(
                    id=new_item_id,
                    name=change.name,
                    quantity=quantity,
                    unit=unit,
                    calories=scaled_nutrition.calories,
                    macros=Macros(
                        protein=scaled_nutrition.protein,
                        carbs=scaled_nutrition.carbs,
                        fat=scaled_nutrition.fat
                    ),
                    confidence=0.9,
                    fdc_id=change.fdc_id,
                    is_custom=False
                )
                logger.info(f"Added food item from nutrition service: {change.name}")
                return

        logger.warning(f"Could not find nutrition data for ingredient: {change.name}")

    def _create_from_custom_nutrition(
        self,
        item_id: str,
        name: str,
        quantity: float,
        unit: str,
        custom_nutrition
    ) -> FoodItem:
        """Create food item from custom nutrition data."""
        scale_factor = quantity / 100.0  # Custom nutrition is per 100g

        return FoodItem(
            id=item_id,
            name=name,
            quantity=quantity,
            unit=unit,
            calories=custom_nutrition.calories_per_100g * scale_factor,
            macros=Macros(
                protein=custom_nutrition.protein_per_100g * scale_factor,
                carbs=custom_nutrition.carbs_per_100g * scale_factor,
                fat=custom_nutrition.fat_per_100g * scale_factor
            ),
            confidence=0.8,
            fdc_id=None,
            is_custom=True
        )


class FoodItemChangeStrategyFactory:
    """Factory for creating appropriate strategy based on action."""

    @staticmethod
    def create_strategies(
        nutrition_service: NutritionCalculationService,
        food_service=None
    ) -> Dict[str, FoodItemChangeStrategy]:
        """Create all available strategies."""
        return {
            "add": AddFoodItemStrategy(nutrition_service, food_service),
            "update": UpdateFoodItemStrategy(nutrition_service),
            "remove": RemoveFoodItemStrategy(nutrition_service)
        }
