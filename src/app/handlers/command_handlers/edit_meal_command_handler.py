"""
Handler for editing meal ingredients.
"""
import logging
import uuid
from typing import Dict, Any, Optional

from src.api.exceptions import ValidationException, ResourceNotFoundException
from src.app.commands.meal import EditMealCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal import MealEditedEvent
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import MealStatus
from src.domain.model.nutrition import FoodItem, Macros
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService
from src.infra.services.pinecone_service import get_pinecone_service

logger = logging.getLogger(__name__)


@handles(EditMealCommand)
class EditMealCommandHandler(EventHandler[EditMealCommand, Dict[str, Any]]):
    """Handler for editing meal ingredients."""

    def __init__(self,
                 meal_repository: MealRepositoryPort = None,
                 food_service=None,
                 nutrition_calculator=None,
                 pinecone_service=None,
                 cache_service: Optional[CacheService] = None):
        self.meal_repository = meal_repository
        self.food_service = food_service
        self.nutrition_calculator = nutrition_calculator
        self.pinecone_service = pinecone_service
        self.cache_service = cache_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.food_service = kwargs.get('food_service', self.food_service)
        self.nutrition_calculator = kwargs.get('nutrition_calculator', self.nutrition_calculator)
        self.pinecone_service = kwargs.get('pinecone_service', self.pinecone_service)
        self.cache_service = kwargs.get('cache_service', self.cache_service)

    async def handle(self, command: EditMealCommand) -> Dict[str, Any]:
        """Handle meal editing operations."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")

        # 1. Validate meal exists
        meal = self.meal_repository.find_by_id(command.meal_id)
        if not meal:
            raise ResourceNotFoundException("Meal not found")

        if meal.status != MealStatus.READY:
            raise ValidationException("Meal must be in READY status to edit")

        # 2. Apply food item changes
        updated_food_items = await self._apply_food_item_changes(
            meal.nutrition.food_items if meal.nutrition else [],
            command.food_item_changes
        )

        # 3. Recalculate nutrition
        updated_nutrition = self._calculate_total_nutrition(updated_food_items)

        # 4. Update meal
        updated_meal = meal.mark_edited(
            nutrition=updated_nutrition,
            dish_name=command.dish_name or meal.dish_name
        )

        # 5. Persist changes
        saved_meal = self.meal_repository.save(updated_meal)
        await self._invalidate_daily_macros(saved_meal)

        # 6. Calculate nutrition delta for event
        nutrition_delta = self._calculate_nutrition_delta(meal.nutrition, updated_nutrition)

        # 7. Generate changes summary
        changes_summary = self._generate_changes_summary(command.food_item_changes)

        return {
            "success": True,
            "meal_id": saved_meal.meal_id,
            "message": f"Meal updated successfully. {changes_summary}",
            "dish_name": saved_meal.dish_name or "Meal",
            "total_calories": updated_nutrition.calories,
            "updated_nutrition": {
                "calories": updated_nutrition.calories,
                "protein": updated_nutrition.macros.protein,
                "carbs": updated_nutrition.macros.carbs,
                "fat": updated_nutrition.macros.fat,
            },
            "updated_food_items": [item.to_dict() for item in updated_food_items],
            "edit_metadata": {
                "edit_count": saved_meal.edit_count,
                "changes_summary": changes_summary
            },
            "events": [
                MealEditedEvent(
                    aggregate_id=saved_meal.meal_id,
                    meal_id=saved_meal.meal_id,
                    user_id=saved_meal.user_id,
                    edit_type="ingredients_updated",
                    changes_summary=changes_summary,
                    nutrition_delta=nutrition_delta,
                    edit_count=saved_meal.edit_count
                )
            ]
        }

    async def _apply_food_item_changes(self, current_food_items, changes):
        """Apply food item changes to current list using strategy pattern."""
        from src.domain.services import NutritionCalculationService
        from src.domain.strategies.meal_edit_strategies import FoodItemChangeStrategyFactory

        # Convert current items to dict for easier manipulation
        food_items_dict = {}
        if current_food_items:
            for item in current_food_items:
                food_items_dict[item.id] = item

        # Initialize nutrition service and create strategies
        nutrition_service = NutritionCalculationService(
            pinecone_service=self.pinecone_service or get_pinecone_service(),
            usda_service=self.food_service
        )
        strategies = FoodItemChangeStrategyFactory.create_strategies(
            nutrition_service,
            self.food_service
        )

        # Apply each change using the appropriate strategy
        for change in changes:
            strategy = strategies.get(change.action)
            if strategy:
                await strategy.apply(food_items_dict, change)
            else:
                logger.warning(f"Unknown action: {change.action}")

        return list(food_items_dict.values())

    async def _get_usda_food_nutrition(self, fdc_id: int, quantity: float):
        """Get nutrition data from USDA service."""
        if not self.food_service:
            raise RuntimeError("Food service not configured")

        # Get food details from USDA
        food_data = await self.food_service.get_food_details(fdc_id)

        # Extract nutrition data (per 100g basis)
        nutrients = food_data.get('foodNutrients', [])

        # Map USDA nutrient IDs to our fields
        nutrient_map = {
            1008: 'calories',  # Energy (kcal)
            1003: 'protein',   # Protein
            1005: 'carbs',     # Carbohydrate, by difference
            1004: 'fat'        # Total lipid (fat)
        }

        nutrition_values = {}
        for nutrient in nutrients:
            nutrient_id = nutrient.get('nutrient', {}).get('id')
            if nutrient_id in nutrient_map:
                nutrition_values[nutrient_map[nutrient_id]] = nutrient.get('amount', 0)

        # Calculate nutrition for the specified quantity
        scale_factor = quantity / 100.0  # USDA data is per 100g

        return FoodItem(
            id=str(uuid.uuid4()),  # Generate new ID for USDA food
            name=food_data.get('description', f"USDA Food {fdc_id}"),
            quantity=quantity,
            unit="g",
            calories=nutrition_values.get('calories', 0) * scale_factor,
            macros=Macros(
                protein=nutrition_values.get('protein', 0) * scale_factor,
                carbs=nutrition_values.get('carbs', 0) * scale_factor,
                fat=nutrition_values.get('fat', 0) * scale_factor,
            ),
            confidence=1.0,
            fdc_id=fdc_id,
            is_custom=False
        )

    def _calculate_total_nutrition(self, food_items):
        """Calculate total nutrition from food items using nutrition service."""
        from src.domain.services import NutritionCalculationService

        nutrition_service = NutritionCalculationService()
        return nutrition_service.calculate_meal_total(food_items)

    def _calculate_nutrition_delta(self, old_nutrition, new_nutrition):
        """Calculate the difference in nutrition values."""
        if not old_nutrition:
            return {
                "calories": new_nutrition.calories,
                "protein": new_nutrition.macros.protein,
                "carbs": new_nutrition.macros.carbs,
                "fat": new_nutrition.macros.fat
            }

        return {
            "calories": new_nutrition.calories - old_nutrition.calories,
            "protein": new_nutrition.macros.protein - old_nutrition.macros.protein,
            "carbs": new_nutrition.macros.carbs - old_nutrition.macros.carbs,
            "fat": new_nutrition.macros.fat - old_nutrition.macros.fat
        }

    def _generate_changes_summary(self, changes):
        """Generate a human-readable summary of changes."""
        summary_parts = []
        for change in changes:
            if change.action == "add":
                summary_parts.append(f"Added {change.name or 'ingredient'}")
            elif change.action == "remove":
                summary_parts.append("Removed ingredient")
            elif change.action == "update":
                summary_parts.append("Updated portion")

        return "; ".join(summary_parts) if summary_parts else "Updated meal"

    async def _invalidate_daily_macros(self, meal):
        if not self.cache_service or not meal:
            return
        created_at = meal.created_at or utc_now()
        cache_key, _ = CacheKeys.daily_macros(meal.user_id, created_at.date())
        await self.cache_service.invalidate(cache_key)
