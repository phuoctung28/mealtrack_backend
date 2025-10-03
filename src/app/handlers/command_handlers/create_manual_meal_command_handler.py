"""
Command handler for creating manual meals from selected USDA foods.
"""
import uuid
from datetime import datetime
from typing import Any, List
from uuid import uuid4

from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand
from src.app.events.base import EventHandler
from src.domain.model.macros import Macros
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_image import MealImage
from src.domain.model.nutrition import Nutrition, FoodItem as DomainFoodItem


class CreateManualMealCommandHandler(EventHandler[CreateManualMealCommand, Any]):
    def __init__(self, meal_repository, food_data_service, mapping_service):
        self.meal_repository = meal_repository
        self.food_data_service = food_data_service
        self.mapping_service = mapping_service

    async def handle(self, event: CreateManualMealCommand):
        # Fetch details for all items
        fdc_ids = [i.fdc_id for i in event.items]
        details_list = await self.food_data_service.get_multiple_foods(fdc_ids)
        details_by_id = {d.get("fdcId"): d for d in details_list}

        # Aggregate nutrition
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        food_items: List[DomainFoodItem] = []

        for item in event.items:
            details = details_by_id.get(item.fdc_id) or {}
            mapped = self.mapping_service.map_food_details(details)
            base_serving = float(mapped.get("serving_size") or 100.0)
            factor = (item.quantity / base_serving) if base_serving > 0 else 0.0

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
                    quantity=item.quantity,
                    unit=item.unit,
                    calories=calories,
                    macros=Macros(
                        protein=protein,
                        carbs=carbs,
                        fat=fat,
                    ),
                    micros=None,
                    confidence=1.0,
                    fdc_id=item.fdc_id,
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

        meal = Meal(
            meal_id=str(uuid4()),
            user_id=event.user_id,
            status=MealStatus.READY,
            created_at=datetime.now(),
            image=MealImage(
                image_id=str(uuid4()),
                format="jpeg",
                size_bytes=1,
                url=None,
            ),
            dish_name=event.dish_name,
            nutrition=nutrition,
            ready_at=datetime.now(),
        )

        return self.meal_repository.save(meal)
