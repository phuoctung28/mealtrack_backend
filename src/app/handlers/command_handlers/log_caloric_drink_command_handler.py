"""Command handler for logging a caloric drink entry."""

import logging
from typing import Optional
from uuid import uuid4

from src.app.commands.hydration.log_caloric_drink_command import LogCaloricDrinkCommand
from src.app.events.base import EventHandler, handles
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.domain.model.hydration import DrinkCategory
from src.domain.model.meal import Meal, MealStatus, MealImage
from src.domain.model.nutrition.nutrition import Nutrition
from src.domain.model.nutrition.macros import Macros
from src.domain.services.hydration_catalog_service import find_by_id, localized_name
from src.infra.database.uow_async import AsyncUnitOfWork
from src.domain.utils.timezone_utils import (
    utc_now,
    noon_utc_for_date,
    resolve_user_timezone_async,
    get_zone_info,
    format_iso_utc,
)

logger = logging.getLogger(__name__)


@handles(LogCaloricDrinkCommand)
class LogCaloricDrinkCommandHandler(EventHandler[LogCaloricDrinkCommand, dict]):
    def __init__(
        self,
        uow: AsyncUnitOfWork,
        cache_invalidation: Optional[CacheInvalidationService] = None,
    ):
        self.uow = uow
        self.cache_invalidation = cache_invalidation

    async def handle(self, cmd: LogCaloricDrinkCommand) -> dict:
        drink = find_by_id(cmd.drink_id)
        if drink is None:
            raise ValueError(f"Unknown drink: {cmd.drink_id}")
        if drink.category != DrinkCategory.CALORIC:
            raise ValueError("Drink is not a caloric drink")

        async with self.uow as uow:
            now = utc_now()
            if cmd.target_date:
                user_tz = await resolve_user_timezone_async(
                    cmd.user_id, uow, cmd.header_timezone
                )
                log_date = cmd.target_date
                log_dt = noon_utc_for_date(log_date, user_tz)
            else:
                log_dt = now
                user_tz = await resolve_user_timezone_async(
                    cmd.user_id, uow, cmd.header_timezone
                )
                tz = get_zone_info(user_tz)
                log_date = log_dt.astimezone(tz).date()

            # Scale macros from per-100ml catalog values
            fat_100ml = max(0.0, (drink.kcal_per_100ml - drink.sugar_per_100ml * 4) / 9)
            carbs_100ml = max(0.0, (drink.kcal_per_100ml - fat_100ml * 9) / 4)
            volume_factor = cmd.volume_ml / 100.0
            credited_ml = drink.credited_ml_for_volume(cmd.volume_ml)

            nutrition = Nutrition(
                macros=Macros(
                    protein=0.0,
                    carbs=round(carbs_100ml * volume_factor, 1),
                    fat=round(fat_100ml * volume_factor, 1),
                    fiber=0.0,
                    sugar=round(drink.sugar_per_100ml * volume_factor, 1),
                ),
                food_items=None,
            )

            meal = Meal(
                meal_id=str(uuid4()),
                user_id=cmd.user_id,
                status=MealStatus.READY,
                created_at=log_dt,
                ready_at=log_dt,
                image=MealImage(
                    image_id=str(uuid4()), format="jpeg", size_bytes=1, url=None
                ),
                dish_name=drink.name,
                emoji=drink.emoji,
                meal_type="hydration",
                source="hydration",
                quantity=credited_ml,
                nutrition=nutrition,
            )
            saved = await uow.meals.save(meal)

        # Synchronous invalidation guarantees Redis is cleared before the response returns
        if self.cache_invalidation:
            await self.cache_invalidation.after_hydration_write(cmd.user_id, log_date)

        kcal = round(saved.nutrition.calories if saved.nutrition else 0.0, 1)
        return {
            "id": saved.meal_id,
            "drink_id": cmd.drink_id,
            "drink_name": localized_name(drink, cmd.language),
            "emoji": drink.emoji,
            "volume_ml": cmd.volume_ml,
            "credited_ml": saved.quantity,
            "kcal": kcal,
            "calories": kcal,
            "source": "hydration",
            "meal_id": saved.meal_id,
            "logged_at": format_iso_utc(saved.created_at),
        }
