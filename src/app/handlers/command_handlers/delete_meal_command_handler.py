"""
Handler for hard-deleting meals with preservation of food item data.

This handler performs:
1. Soft-delete food_items (is_deleted=True, nutrition_id=NULL)
2. Soft-delete meal_translations (is_deleted=True, meal_id=NULL) - prevents DB cascade
3. Soft-delete food_item_translations (is_deleted=True)
4. Hard-delete nutrition
5. Hard-delete meal

MealImage records are kept as orphans (images stay in storage).
"""
import logging
from typing import Any, Dict, Optional

from sqlalchemy import update

from src.api.exceptions import ResourceNotFoundException, AuthorizationException
from src.app.commands.meal import DeleteMealCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal.meal_cache_invalidation_required_event import MealCacheInvalidationRequiredEvent
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.meal.meal import MealORM
from src.infra.database.models.meal.meal_translation_model import MealTranslationORM
from src.infra.database.models.meal.food_item_translation_model import FoodItemTranslationORM
from src.infra.database.models.nutrition.nutrition import NutritionORM
from src.infra.database.models.nutrition.food_item import FoodItemORM

logger = logging.getLogger(__name__)


@handles(DeleteMealCommand)
class DeleteMealCommandHandler(EventHandler[DeleteMealCommand, Dict[str, Any]]):
    """Handler for hard-deleting a meal with data preservation."""

    def __init__(self, uow: UnitOfWorkPort, event_bus: Any):
        self.uow = uow
        self.event_bus = event_bus

    async def handle(self, command: DeleteMealCommand) -> Dict[str, Any]:
        """Handle meal deletion with data preservation."""
        with self.uow as uow:
            try:
                # Get meal
                meal = uow.meals.find_by_id(command.meal_id)
                if not meal:
                    raise ResourceNotFoundException(f"Meal with ID {command.meal_id} not found")

                # Verify ownership - only meal owner can delete
                if meal.user_id != command.user_id:
                    raise AuthorizationException(
                        "You do not have permission to delete this meal"
                    )

                meal_id = command.meal_id

                # --- Step 1: Soft-delete children + detach FKs ---

                # 1a. Soft-delete food_items + nullify nutrition FK
                # Get nutrition first
                nutrition = uow.session.query(NutritionORM).filter(
                    NutritionORM.meal_id == meal_id
                ).first()

                if nutrition:
                    nutrition_id = nutrition.id
                    # Soft-delete food_items and nullify FK
                    uow.session.execute(
                        update(FoodItemORM)
                        .where(FoodItemORM.nutrition_id == nutrition_id)
                        .values(is_deleted=True, nutrition_id=None)
                    )

                # 1b. Soft-delete meal_translations + nullify meal FK (prevents DB cascade)
                # Get meal_translation IDs BEFORE nullifying
                meal_translation_ids = [
                    mt.id for mt in uow.session.query(MealTranslationORM.id).filter(
                        MealTranslationORM.meal_id == meal_id
                    ).all()
                ]

                # Now nullify meal_id to prevent cascade
                uow.session.execute(
                    update(MealTranslationORM)
                    .where(MealTranslationORM.meal_id == meal_id)
                    .values(is_deleted=True, meal_id=None)
                )

                # 1c. Soft-delete food_item_translations using stored IDs
                # Use the IDs stored BEFORE nullifying

                if meal_translation_ids:
                    uow.session.execute(
                        update(FoodItemTranslationORM)
                        .where(FoodItemTranslationORM.meal_translation_id.in_(meal_translation_ids))
                        .values(is_deleted=True)
                    )

                # --- Step 2: Hard-delete parents ---

                # 2a. Hard-delete nutrition (food_items already detached)
                uow.session.execute(
                    NutritionORM.__table__.delete().where(NutritionORM.meal_id == meal_id)
                )

                # 2b. Hard-delete meal (translations already detached)
                uow.session.execute(
                    MealORM.__table__.delete().where(MealORM.meal_id == meal_id)
                )

                uow.commit()

                meal_date = (meal.created_at or utc_now()).date()
                await self.event_bus.publish(MealCacheInvalidationRequiredEvent(
                    aggregate_id=meal.user_id,
                    user_id=meal.user_id,
                    meal_date=meal_date,
                ))

                return {
                    "meal_id": meal_id,
                    "message": "Meal deleted, ingredient data preserved"
                }
            except Exception as e:
                uow.rollback()
                logger.error(f"Error deleting meal: {str(e)}")
                raise
