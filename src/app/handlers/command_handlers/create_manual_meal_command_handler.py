"""
Command handler for creating manual meals from selected USDA foods.
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand
from src.app.events.base import EventHandler
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal import MealImage
from src.domain.model.nutrition import Macros
from src.domain.model.nutrition import Nutrition, FoodItem as DomainFoodItem
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService


class CreateManualMealCommandHandler(EventHandler[CreateManualMealCommand, Any]):
    def __init__(self, food_data_service, mapping_service, cache_service: Optional[CacheService] = None, meal_repository: Optional[MealRepositoryPort] = None):
        self.meal_repository = meal_repository
        self.food_data_service = food_data_service
        self.mapping_service = mapping_service
        self.cache_service = cache_service

    async def handle(self, event: CreateManualMealCommand):
        # Use UnitOfWork for meal repository if not provided
        from src.infra.database.uow import UnitOfWork
        
        uow = UnitOfWork() if not self.meal_repository else None
        meal_repo = self.meal_repository or (uow.meals if uow else None)
        
        if not meal_repo:
            raise RuntimeError("Meal repository not available")
        
        # Aggregate items with the same fdc_id first
        from collections import defaultdict
        aggregated_items = defaultdict(lambda: {"quantity": 0.0, "unit": "g"})
        
        for item in event.items:
            aggregated_items[item.fdc_id]["quantity"] += item.quantity
            aggregated_items[item.fdc_id]["unit"] = item.unit
        
        # Fetch details for all unique items
        fdc_ids = list(aggregated_items.keys())
        details_list = await self.food_data_service.get_multiple_foods(fdc_ids)
        details_by_id = {d.get("fdcId"): d for d in details_list}

        # Calculate nutrition
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        food_items: List[DomainFoodItem] = []

        for fdc_id, item_data in aggregated_items.items():
            details = details_by_id.get(fdc_id) or {}
            mapped = self.mapping_service.map_food_details(details)
            base_serving = float(mapped.get("serving_size") or 100.0)
            quantity = item_data["quantity"]
            factor = (quantity / base_serving) if base_serving > 0 else 0.0

            calories = float(mapped.get("calories") or 0.0) * factor
            protein = float(mapped["macros"].get("protein") or 0.0) * factor
            carbs = float(mapped["macros"].get("carbs") or 0.0) * factor
            fat = float(mapped["macros"].get("fat") or 0.0) * factor

            total_calories += calories
            total_protein += protein
            total_carbs += carbs
            total_fat += fat

            food_items.append(
                DomainFoodItem(
                    id=uuid.uuid4(),
                    name=mapped.get("name"),
                    quantity=quantity,
                    unit=item_data["unit"],
                    calories=calories,
                    macros=Macros(
                        protein=protein,
                        carbs=carbs,
                        fat=fat,
                    ),
                    micros=None,
                    confidence=1.0,
                    fdc_id=fdc_id,
                )
            )

        nutrition = Nutrition(
            calories=round(total_calories, 1),
            macros=Macros(
                protein=round(total_protein, 1),
                carbs=round(total_carbs, 1),
                fat=round(total_fat, 1),
            ),
            food_items=food_items,
            confidence_score=1.0,
        )

        # Determine the meal date - use target_date if provided, otherwise use now
        meal_date = event.target_date if event.target_date else utc_now().date()
        meal_datetime = datetime.combine(meal_date, utc_now().time())
        
        meal = Meal(
            meal_id=str(uuid4()),
            user_id=event.user_id,
            status=MealStatus.READY,
            created_at=meal_datetime,
            image=MealImage(
                image_id=str(uuid4()),
                format="jpeg",
                size_bytes=1,
                url=None,
            ),
            dish_name=event.dish_name,
            nutrition=nutrition,
            ready_at=meal_datetime,
            meal_type=event.meal_type,
        )

        saved_meal = meal_repo.save(meal)
        
        # Commit if using UoW
        if uow:
            uow.commit()
            uow.session.close()
            
        await self._invalidate_daily_macros(event.user_id, meal_date)
        return saved_meal

    async def _invalidate_daily_macros(self, user_id, target_date):
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.daily_macros(user_id, target_date)
        await self.cache_service.invalidate(cache_key)
