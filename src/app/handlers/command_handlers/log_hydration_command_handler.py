"""Command handler for logging a hydration (non-caloric) drink entry."""

import logging
from datetime import date, timedelta
from typing import Any, Optional
from uuid import uuid4

from src.app.commands.hydration.log_hydration_command import LogHydrationCommand
from src.app.events.base import EventHandler, handles
from src.app.events.hydration.hydration_cache_invalidation_required_event import (
    HydrationCacheInvalidationRequiredEvent,
)
from src.app.events.meal.meal_cache_invalidation_required_event import (
    MealCacheInvalidationRequiredEvent,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.hydration import DrinkCategory
from src.domain.model.meal import Meal, MealStatus, MealImage
from src.domain.model.nutrition.nutrition import Nutrition
from src.domain.model.nutrition.macros import Macros
from src.domain.ports.cache_port import CachePort
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


async def _flush_hydration_caches(
    cache: CachePort, user_id: str, log_date: date
) -> None:
    """Synchronously flush all caches affected by a hydration mutation."""
    week_start = log_date - timedelta(days=log_date.weekday())
    keys_to_delete = [
        CacheKeys.weekly_hydration(user_id, week_start)[0],
        CacheKeys.daily_macros(user_id, log_date)[0],
    ]
    for key in keys_to_delete:
        try:
            await cache.invalidate(key)
        except Exception as exc:
            logger.warning("Cache invalidation failed for key=%s: %s", key, exc)

    activities_pattern = f"user:{user_id}:activities:{log_date.isoformat()}:*"
    try:
        await cache.invalidate_pattern(activities_pattern)
    except Exception as exc:
        logger.warning(
            "Cache pattern invalidation failed for %s: %s", activities_pattern, exc
        )

    hydration_pattern = f"user:{user_id}:hydration:{log_date.isoformat()}:*"
    try:
        await cache.invalidate_pattern(hydration_pattern)
    except Exception as exc:
        logger.warning(
            "Cache pattern invalidation failed for %s: %s", hydration_pattern, exc
        )


@handles(LogHydrationCommand)
class LogHydrationCommandHandler(EventHandler[LogHydrationCommand, dict]):
    def __init__(
        self,
        uow: AsyncUnitOfWork,
        event_bus: Any,
        cache_service: Optional[CachePort] = None,
    ):
        self.uow = uow
        self.event_bus = event_bus
        self.cache_service = cache_service

    async def handle(self, cmd: LogHydrationCommand) -> dict:
        drink = find_by_id(cmd.drink_id)
        if drink is None:
            raise ValueError(f"Unknown drink: {cmd.drink_id}")
        if drink.category != DrinkCategory.HYDRATION:
            raise ValueError("Drink is not a hydration drink")

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

            credited_ml = drink.credited_ml_for_volume(cmd.volume_ml)
            if drink.kcal_per_100ml > 0:
                fat_100ml = max(0.0, (drink.kcal_per_100ml - drink.sugar_per_100ml * 4) / 9)
                carbs_100ml = max(0.0, (drink.kcal_per_100ml - fat_100ml * 9) / 4)
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
            else:
                nutrition = Nutrition(
                    macros=Macros(protein=0.0, carbs=0.0, fat=0.0, fiber=0.0, sugar=0.0),
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

        # Synchronous cache flush (before fire-and-forget event bus publish)
        if self.cache_service:
            await _flush_hydration_caches(self.cache_service, cmd.user_id, log_date)

        await self.event_bus.publish(
            MealCacheInvalidationRequiredEvent(
                aggregate_id=cmd.user_id,
                user_id=cmd.user_id,
                meal_date=log_date,
            )
        )
        await self.event_bus.publish(
            HydrationCacheInvalidationRequiredEvent(
                aggregate_id=cmd.user_id,
                user_id=cmd.user_id,
                hydration_date=log_date,
            )
        )
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
