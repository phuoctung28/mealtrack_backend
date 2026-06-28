"""
Handler for editing meal ingredients.
"""

import logging
from typing import Any

from src.api.exceptions import (
    AuthorizationException,
    ResourceNotFoundException,
    ValidationException,
)
from src.app.commands.meal import EditMealCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal import MealEditedEvent
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.domain.model.meal import FoodItemTranslation, MealStatus
from src.domain.model.meal_projection import MealProjection
from src.domain.services.meal_type_determination_service import (
    determine_meal_type_from_timestamp,
)
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


@handles(EditMealCommand)
class EditMealCommandHandler(EventHandler[EditMealCommand, dict[str, Any]]):
    """Handler for editing meal ingredients."""

    def __init__(
        self,
        uow: AsyncUnitOfWorkPort,
        cache_invalidation: CacheInvalidationService | None = None,
    ):
        self.uow = uow
        self.cache_invalidation = cache_invalidation

    async def handle(self, command: EditMealCommand) -> dict[str, Any]:
        """Handle meal editing operations."""
        async with self.uow as uow:
            try:
                # 1. Validate meal exists
                meal = await uow.meals.find_by_id(
                    command.meal_id, projection=MealProjection.FULL_WITH_TRANSLATIONS
                )
                if not meal:
                    raise ResourceNotFoundException("Meal not found")

                # 1a. Check ownership if user_id provided
                if command.user_id and meal.user_id != command.user_id:
                    raise AuthorizationException(
                        "You do not have permission to modify this meal"
                    )

                if meal.status != MealStatus.READY:
                    raise ValidationException("Meal must be in READY status to edit")

                # 2. Apply food item changes
                updated_food_items = await self._apply_food_item_changes(
                    meal.nutrition.food_items if meal.nutrition else [],
                    command.food_item_changes,
                )
                self._realign_translations_after_food_item_changes(
                    meal, updated_food_items
                )

                # 3. Recalculate nutrition
                updated_nutrition = self._calculate_total_nutrition(updated_food_items)

                updated_created_at = command.created_at or meal.created_at
                if command.meal_type is not None:
                    updated_meal_type = command.meal_type
                elif command.created_at is not None:
                    updated_meal_type = determine_meal_type_from_timestamp(
                        command.created_at
                    )
                else:
                    updated_meal_type = meal.meal_type

                # 4. Update meal
                updated_meal = meal.mark_edited(
                    nutrition=updated_nutrition,
                    dish_name=(
                        command.dish_name
                        if command.dish_name is not None
                        else meal.dish_name
                    ),
                    created_at=updated_created_at,
                    meal_type=updated_meal_type,
                )

                # 5. Persist changes
                saved_meal = await uow.meals.save(updated_meal)
                await self._save_realigned_translations(uow, updated_meal.translations)
                await uow.commit()

                old_meal_date = (meal.created_at or utc_now()).date()
                meal_date = (saved_meal.created_at or utc_now()).date()
                if self.cache_invalidation:
                    if old_meal_date != meal_date:
                        await self.cache_invalidation.after_meal_write(
                            saved_meal.user_id, old_meal_date
                        )
                    await self.cache_invalidation.after_meal_write(
                        saved_meal.user_id, meal_date
                    )

                # 6. Calculate nutrition delta for event
                nutrition_delta = self._calculate_nutrition_delta(
                    meal.nutrition, updated_nutrition
                )

                # 7. Generate changes summary
                changes_summary = self._generate_changes_summary(
                    command.food_item_changes
                )

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
                    "updated_food_items": [
                        item.to_dict() for item in updated_food_items
                    ],
                    "edit_metadata": {
                        "edit_count": saved_meal.edit_count,
                        "changes_summary": changes_summary,
                    },
                    "events": [
                        MealEditedEvent(
                            aggregate_id=saved_meal.meal_id,
                            meal_id=saved_meal.meal_id,
                            user_id=saved_meal.user_id,
                            edit_type="ingredients_updated",
                            changes_summary=changes_summary,
                            nutrition_delta=nutrition_delta,
                            edit_count=saved_meal.edit_count,
                        )
                    ],
                }
            except ValueError as e:
                await uow.rollback()
                logger.warning(f"Validation error editing meal: {str(e)}")
                raise ValidationException(str(e)) from None
            except Exception:
                await uow.rollback()
                raise

    async def _apply_food_item_changes(self, current_food_items, changes):
        """Apply food item changes to current list using strategy pattern."""
        from src.domain.services import NutritionCalculationService
        from src.domain.strategies.meal_edit_strategies import (
            FoodItemChangeStrategyFactory,
        )

        # Convert current items to dict for easier manipulation
        food_items_dict = {}
        if current_food_items:
            for item in current_food_items:
                food_items_dict[item.id] = item

        # Initialize nutrition service and create strategies
        nutrition_service = NutritionCalculationService()
        strategies = FoodItemChangeStrategyFactory.create_strategies(
            nutrition_service,
        )

        # Apply each change using the appropriate strategy
        for change in changes:
            strategy = strategies.get(change.action)
            if strategy:
                await strategy.apply(food_items_dict, change)
            else:
                logger.warning(f"Unknown action: {change.action}")

        return list(food_items_dict.values())

    def _realign_translations_after_food_item_changes(self, meal, updated_food_items):
        """Keep cached translations aligned to the edited food item order."""
        if not meal.translations or not meal.nutrition or not meal.nutrition.food_items:
            return

        previous_food_items = meal.nutrition.food_items
        for translation in meal.translations.values():
            translated_names_by_id = self._translated_names_by_id(
                translation, previous_food_items
            )
            if not translated_names_by_id:
                continue

            realigned_ingredients = []
            realigned_food_items = []
            for item in updated_food_items:
                translated_name = translated_names_by_id.get(str(item.id), item.name)
                realigned_ingredients.append(translated_name)
                realigned_food_items.append(
                    FoodItemTranslation(
                        food_item_id=str(item.id),
                        name=translated_name,
                    )
                )

            translation.meal_ingredients = realigned_ingredients
            translation.food_items = realigned_food_items

    def _translated_names_by_id(self, translation, previous_food_items):
        translated_names_by_id = {
            str(item.food_item_id): item.name
            for item in translation.food_items
            if item.name
        }
        if translated_names_by_id:
            return translated_names_by_id

        if translation.meal_ingredients and len(translation.meal_ingredients) == len(
            previous_food_items
        ):
            return {
                str(item.id): translation.meal_ingredients[index]
                for index, item in enumerate(previous_food_items)
                if translation.meal_ingredients[index]
            }

        return {}

    async def _save_realigned_translations(self, uow, translations):
        if not translations:
            return

        translation_repo = getattr(uow, "meal_translations", None)
        if translation_repo is None:
            return

        for translation in translations.values():
            await translation_repo.save(translation)

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
                "fat": new_nutrition.macros.fat,
            }

        return {
            "calories": new_nutrition.calories - old_nutrition.calories,
            "protein": new_nutrition.macros.protein - old_nutrition.macros.protein,
            "carbs": new_nutrition.macros.carbs - old_nutrition.macros.carbs,
            "fat": new_nutrition.macros.fat - old_nutrition.macros.fat,
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
