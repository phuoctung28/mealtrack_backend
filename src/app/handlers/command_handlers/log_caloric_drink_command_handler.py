"""Command handler for logging a caloric drink entry."""

import logging
from typing import Any, Optional
from uuid import uuid4

from src.app.commands.hydration.log_caloric_drink_command import LogCaloricDrinkCommand
from src.app.events.base import EventHandler, handles
from src.app.events.hydration.hydration_cache_invalidation_required_event import (
    HydrationCacheInvalidationRequiredEvent,
)
from src.app.events.meal.meal_cache_invalidation_required_event import (
    MealCacheInvalidationRequiredEvent,
)
from src.domain.model.meal import Meal, MealStatus, MealImage
from src.domain.model.nutrition.nutrition import Nutrition
from src.domain.model.nutrition.macros import Macros
from src.domain.ports.cache_port import CachePort
from src.domain.services.hydration_catalog_service import find_by_id
from src.infra.database.uow_async import AsyncUnitOfWork
from src.domain.utils.timezone_utils import (
    utc_now,
    noon_utc_for_date,
    resolve_user_timezone_async,
    get_zone_info,
    format_iso_utc,
)
from src.app.handlers.command_handlers.log_hydration_command_handler import (
    _flush_hydration_caches,
)

logger = logging.getLogger(__name__)


@handles(LogCaloricDrinkCommand)
class LogCaloricDrinkCommandHandler(EventHandler[LogCaloricDrinkCommand, dict]):
    def __init__(self, uow: AsyncUnitOfWork, event_bus: Any, cache_service: Optional[CachePort] = None):
        self.uow = uow
        self.event_bus = event_bus
        self.cache_service = cache_service

    async def handle(self, cmd: LogCaloricDrinkCommand) -> dict:
        drink = find_by_id(cmd.drink_id)
        if drink is None:
            raise ValueError(f"Unknown drink: {cmd.drink_id}")

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
            carbs_100ml = drink.sugar_per_100ml
            fat_100ml = max(0.0, (drink.kcal_per_100ml - carbs_100ml * 4) / 9)
            volume_factor = cmd.volume_ml / 100.0

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
                image=MealImage(image_id=str(uuid4()), format="jpeg", size_bytes=1, url=None),
                dish_name=drink.name,
                emoji=drink.emoji,
                meal_type="hydration",
                source="hydration",
                quantity=cmd.volume_ml,
                nutrition=nutrition,
            )
            saved = await uow.meals.save(meal)

        if self.cache_service:
            await _flush_hydration_caches(self.cache_service, cmd.user_id, log_date)

        await self.event_bus.publish(
            MealCacheInvalidationRequiredEvent(
                aggregate_id=cmd.user_id, user_id=cmd.user_id, meal_date=log_date,
            )
        )
        await self.event_bus.publish(
            HydrationCacheInvalidationRequiredEvent(
                aggregate_id=cmd.user_id, user_id=cmd.user_id, hydration_date=log_date,
            )
        )
        kcal = round(
            (saved.nutrition.macros.carbs * 4 + saved.nutrition.macros.fat * 9)
            if saved.nutrition
            else 0.0,
            1,
        )
        return {
            "id": saved.meal_id,
            "drink_id": cmd.drink_id,
            "drink_name": drink.name,
            "emoji": drink.emoji,
            "volume_ml": saved.quantity,
            "kcal": kcal,
            "source": "hydration",
            "meal_id": saved.meal_id,
            "logged_at": format_iso_utc(saved.created_at),
        }
