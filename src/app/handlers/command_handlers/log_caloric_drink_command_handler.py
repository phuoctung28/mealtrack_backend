"""Command handler for logging a caloric drink (creates a meal + hydration entry atomically)."""

import logging
from typing import Any
from uuid import uuid4

from src.app.commands.hydration.log_caloric_drink_command import LogCaloricDrinkCommand
from src.app.events.base import EventHandler, handles
from src.app.events.hydration.hydration_cache_invalidation_required_event import (
    HydrationCacheInvalidationRequiredEvent,
)
from src.app.events.meal.meal_cache_invalidation_required_event import (
    MealCacheInvalidationRequiredEvent,
)
from src.domain.model.hydration import HydrationEntry, DrinkCategory, HydrationSource
from src.domain.model.meal import Meal, MealStatus, MealImage
from src.domain.model.nutrition.nutrition import Nutrition
from src.domain.model.nutrition.macros import Macros
from src.domain.services.hydration_catalog_service import find_by_id
from src.infra.database.uow_async import AsyncUnitOfWork
from src.domain.utils.timezone_utils import (
    utc_now,
    noon_utc_for_date,
    resolve_user_timezone_async,
    get_zone_info,
)

logger = logging.getLogger(__name__)


@handles(LogCaloricDrinkCommand)
class LogCaloricDrinkCommandHandler(EventHandler[LogCaloricDrinkCommand, dict]):
    def __init__(self, uow: AsyncUnitOfWork, event_bus: Any):
        self.uow = uow
        self.event_bus = event_bus

    async def handle(self, cmd: LogCaloricDrinkCommand) -> dict:
        # 1. Validate drink
        drink = find_by_id(cmd.drink_id)
        if drink is None:
            raise ValueError(f"Unknown drink: {cmd.drink_id}")
        if drink.category != DrinkCategory.CALORIC:
            raise ValueError(
                f"Drink {cmd.drink_id} is not caloric — use LogHydrationCommand"
            )

        async with self.uow as uow:
            # 2. Resolve datetime
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

            # 3. Scale macros from drink catalog values
            # kcal per 100ml decomposed into carbs (sugar) + fat; protein=0, fiber=0
            carbs_100ml = drink.sugar_per_100ml
            fat_100ml = max(0.0, (drink.kcal_per_100ml - carbs_100ml * 4) / 9)
            protein_100ml = 0.0
            volume_factor = cmd.volume_ml / 100.0

            nutrition = Nutrition(
                macros=Macros(
                    protein=round(protein_100ml * volume_factor, 1),
                    carbs=round(carbs_100ml * volume_factor, 1),
                    fat=round(fat_100ml * volume_factor, 1),
                    fiber=0.0,
                    sugar=round(drink.sugar_per_100ml * volume_factor, 1),
                ),
                food_items=None,
            )

            # 4. Create Meal (same pattern as CreateManualMealCommandHandler)
            meal = Meal(
                meal_id=str(uuid4()),
                user_id=cmd.user_id,
                status=MealStatus.READY,
                created_at=log_dt,
                image=MealImage(
                    image_id=str(uuid4()),
                    format="jpeg",
                    size_bytes=1,
                    url=None,
                ),
                dish_name=f"{drink.name} · {cmd.volume_ml}ml",
                emoji=drink.emoji,
                nutrition=nutrition,
                ready_at=log_dt,
                meal_type="snack",
                source="manual",
            )
            saved_meal = await uow.meals.save(meal)

            # 5. Create HydrationEntry linked to this meal
            credited_ml = drink.credited_ml_for_volume(cmd.volume_ml)
            entry = HydrationEntry(
                entry_id=str(uuid4()),
                user_id=cmd.user_id,
                drink_id=cmd.drink_id,
                volume_ml=cmd.volume_ml,
                credited_ml=credited_ml,
                source=HydrationSource.CALORIC_DRINK,
                meal_id=saved_meal.meal_id,
                logged_at=log_dt,
                created_at=utc_now(),
                is_deleted=False,
            )
            saved_entry = await uow.hydration_logs.save(entry)

        # 6. Publish both cache invalidation events
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
        return {"entry_id": saved_entry.entry_id, "meal_id": saved_meal.meal_id}
