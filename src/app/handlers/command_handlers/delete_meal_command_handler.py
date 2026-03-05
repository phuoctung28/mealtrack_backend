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
from typing import Dict, Any, Optional

from sqlalchemy import update

from src.api.exceptions import ResourceNotFoundException, AuthorizationException
from src.app.commands.meal import DeleteMealCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService
from src.infra.database.models.meal.meal import Meal as MealModel
from src.infra.database.models.meal.meal_translation_model import MealTranslation
from src.infra.database.models.meal.food_item_translation_model import FoodItemTranslation
from src.infra.database.models.nutrition.nutrition import Nutrition
from src.infra.database.models.nutrition.food_item import FoodItem
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(DeleteMealCommand)
class DeleteMealCommandHandler(EventHandler[DeleteMealCommand, Dict[str, Any]]):
    """Handler for hard-deleting a meal with data preservation."""

    def __init__(self, uow: Optional[UnitOfWorkPort] = None, cache_service: Optional[CacheService] = None):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, command: DeleteMealCommand) -> Dict[str, Any]:
        """Handle meal deletion with data preservation."""
        uow = self.uow or UnitOfWork()

        with uow:
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
                nutrition = uow.session.query(Nutrition).filter(
                    Nutrition.meal_id == meal_id
                ).first()

                if nutrition:
                    nutrition_id = nutrition.id
                    # Soft-delete food_items and nullify FK
                    uow.session.execute(
                        update(FoodItem)
                        .where(FoodItem.nutrition_id == nutrition_id)
                        .values(is_deleted=True, nutrition_id=None)
                    )

                # 1b. Soft-delete meal_translations + nullify meal FK (prevents DB cascade)
                # Get meal_translation IDs BEFORE nullifying
                meal_translation_ids = [
                    mt.id for mt in uow.session.query(MealTranslation.id).filter(
                        MealTranslation.meal_id == meal_id
                    ).all()
                ]

                # Now nullify meal_id to prevent cascade
                uow.session.execute(
                    update(MealTranslation)
                    .where(MealTranslation.meal_id == meal_id)
                    .values(is_deleted=True, meal_id=None)
                )

                # 1c. Soft-delete food_item_translations using stored IDs
                # Use the IDs stored BEFORE nullifying

                if meal_translation_ids:
                    uow.session.execute(
                        update(FoodItemTranslation)
                        .where(FoodItemTranslation.meal_translation_id.in_(meal_translation_ids))
                        .values(is_deleted=True)
                    )

                # --- Step 2: Hard-delete parents ---

                # 2a. Hard-delete nutrition (food_items already detached)
                uow.session.execute(
                    Nutrition.__table__.delete().where(Nutrition.meal_id == meal_id)
                )

                # 2b. Hard-delete meal (translations already detached)
                uow.session.execute(
                    MealModel.__table__.delete().where(MealModel.meal_id == meal_id)
                )

                uow.commit()

                await self._invalidate_daily_macros(meal)

                return {
                    "meal_id": meal_id,
                    "message": "Meal deleted, ingredient data preserved"
                }
            except Exception as e:
                uow.rollback()
                logger.error(f"Error deleting meal: {str(e)}")
                raise

    async def _invalidate_daily_macros(self, meal):
        if not self.cache_service or not meal:
            return
        created_at = meal.created_at or utc_now()
        cache_key, _ = CacheKeys.daily_macros(meal.user_id, created_at.date())
        await self.cache_service.invalidate(cache_key)
