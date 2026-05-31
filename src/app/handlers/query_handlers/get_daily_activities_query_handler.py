"""
GetDailyActivitiesQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.activity import GetDailyActivitiesQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import Meal
from src.domain.services.hydration_catalog_service import (
    localized_name_for_catalog_name,
)
from src.domain.utils.timezone_utils import (
    format_iso_utc,
    get_zone_info,
    resolve_user_timezone_async,
)
from src.domain.ports.cache_port import CachePort
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(GetDailyActivitiesQuery)
class GetDailyActivitiesQueryHandler(
    EventHandler[GetDailyActivitiesQuery, List[Dict[str, Any]]]
):
    """Handler for getting daily activities (meals and workouts)."""

    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(self, query: GetDailyActivitiesQuery) -> List[Dict[str, Any]]:
        """Get all activities for the specified date."""
        raw = query.target_date
        if hasattr(raw, "tzinfo") and raw.tzinfo is not None and query.header_timezone:
            target_date = raw.astimezone(get_zone_info(query.header_timezone)).date()
        elif hasattr(raw, "date"):
            target_date = raw.date()
        else:
            target_date = raw
        cache_key, ttl = CacheKeys.daily_activities(
            query.user_id, target_date, query.language or "en"
        )
        if self.cache_service:
            cached = await self.cache_service.get_json(cache_key)
            if cached is not None:
                return cached

        meal_activities = await self._get_meal_activities(query)
        workout_activities = await self._get_workout_activities(query)
        activities = meal_activities + workout_activities
        logger.info(
            f"Retrieved {len(activities)} activities for user {query.user_id} on {query.target_date.strftime('%Y-%m-%d')}"
        )
        if self.cache_service:
            await self.cache_service.set_json(cache_key, activities, ttl)
        return activities

    async def _get_meal_activities(
        self,
        query: GetDailyActivitiesQuery,
    ) -> List[Dict[str, Any]]:
        """Fetch meals and hydration logs for the query date/user."""
        try:
            async with AsyncUnitOfWork() as uow:
                user_tz_str = await resolve_user_timezone_async(
                    query.user_id, uow, query.header_timezone
                )

                tz = get_zone_info(user_tz_str)
                target_date = query.target_date
                date_obj = (
                    target_date.date()
                    if target_date.tzinfo is None
                    else target_date.astimezone(tz).date()
                )

                items = await uow.meals.find_by_date(
                    date_obj,
                    user_id=query.user_id,
                    user_timezone=user_tz_str,
                )

                return [
                    (
                        self._build_hydration_activity(item, query.language or "en")
                        if item.meal_type == "hydration"
                        else self._build_meal_activity(
                            item, target_date, query.language
                        )
                    )
                    for item in items
                ]

        except Exception as e:
            logger.error(f"Error getting meal activities: {str(e)}", exc_info=True)
            return []

    async def _get_workout_activities(
        self,
        query: GetDailyActivitiesQuery,
    ) -> List[Dict[str, Any]]:
        """Fetch movement entries for the query date/user."""
        try:
            from datetime import time, timedelta, timezone

            async with AsyncUnitOfWork() as uow:
                user_tz_str = await resolve_user_timezone_async(
                    query.user_id, uow, query.header_timezone
                )
                tz = get_zone_info(user_tz_str)
                # Mirror the meals path: convert tz-aware datetimes to user-local
                # before extracting the date, so the no-`date` route (utc_now())
                # uses the correct local day for UTC+N users.
                raw = query.target_date
                if hasattr(raw, "tzinfo") and raw.tzinfo is not None:
                    target_date = raw.astimezone(tz).date()
                elif hasattr(raw, "date"):
                    target_date = raw.date()
                else:
                    target_date = raw
                start_utc = datetime.combine(target_date, time.min, tzinfo=tz).astimezone(timezone.utc)
                end_utc = start_utc + timedelta(days=1)

                entries = await uow.movement_entries.find_by_user_and_logged_range(
                    query.user_id, start_utc, end_utc
                )

            return [self._build_movement_activity(entry) for entry in entries]
        except Exception as e:
            logger.error(f"Error getting workout activities: {str(e)}", exc_info=True)
            return []

    def _build_movement_activity(self, entry) -> Dict[str, Any]:
        return {
            "id": entry.id,
            "type": "movement",
            "timestamp": format_iso_utc(entry.logged_at),
            "title": entry.activity_name,
            "activity_id": entry.activity_id,
            "intensity": entry.intensity,
            "duration_min": entry.duration_min,
            "kcal_burned": entry.kcal_burned,
            "source": entry.source,
            "include_in_balance": entry.include_in_balance,
        }

    def _build_meal_activity(
        self, meal, target_date: datetime, language: str = "en"
    ) -> Dict[str, Any]:
        meal_type = (
            meal.meal_type
            if hasattr(meal, "meal_type") and meal.meal_type
            else self._determine_meal_type(meal.created_at)
        )
        estimated_weight = self._estimate_meal_weight(meal)
        image_url = meal.image.url if hasattr(meal, "image") and meal.image else None

        title = meal.dish_name or "Unknown Meal"
        if language and language != "en" and meal.translations:
            translation = meal.translations.get(language)
            if translation and translation.dish_name:
                title = translation.dish_name

        return {
            "id": meal.meal_id,
            "type": "meal",
            "timestamp": (
                format_iso_utc(meal.created_at)
                if meal.created_at
                else format_iso_utc(target_date)
            ),
            "title": title,
            "emoji": getattr(meal, "emoji", None),
            "meal_type": meal_type,
            "calories": round(meal.nutrition.calories, 1) if meal.nutrition else 0,
            "macros": {
                "protein": (
                    round(meal.nutrition.macros.protein, 1) if meal.nutrition else 0
                ),
                "carbs": round(meal.nutrition.macros.carbs, 1) if meal.nutrition else 0,
                "fat": round(meal.nutrition.macros.fat, 1) if meal.nutrition else 0,
            },
            "quantity": estimated_weight,
            "status": meal.status.value if meal.status else "unknown",
            "image_url": image_url,
            "source": getattr(meal, "source", None),
        }

    def _build_hydration_activity(
        self, meal: Meal, language: str = "en"
    ) -> Dict[str, Any]:
        kcal = round(meal.nutrition.calories, 1) if meal.nutrition else 0
        macros = {
            "protein": round(meal.nutrition.macros.protein, 1) if meal.nutrition else 0,
            "carbs": round(meal.nutrition.macros.carbs, 1) if meal.nutrition else 0,
            "fat": round(meal.nutrition.macros.fat, 1) if meal.nutrition else 0,
        }
        return {
            "id": meal.meal_id,
            "type": "hydration",
            "timestamp": format_iso_utc(meal.created_at),
            "title": localized_name_for_catalog_name(meal.dish_name, language)
            or "Water",
            "emoji": meal.emoji or "💧",
            "meal_type": "hydration",
            "calories": kcal,
            "macros": macros,
            "quantity": meal.quantity or 0,
            "volume_ml": meal.quantity or 0,
            "status": "completed",
            "image_url": None,
            "source": meal.source or "hydration",
        }

    def _estimate_meal_weight(self, meal) -> float:
        """Estimate meal weight from nutrition data."""
        # Default weight
        estimated_weight = 300.0

        # Check if meal has updated weight
        if hasattr(meal, "weight_grams"):
            return meal.weight_grams

        # Try to get from food items
        if meal.nutrition and meal.nutrition.food_items:
            first_food = meal.nutrition.food_items[0]
            if first_food.unit and "g" in first_food.unit.lower():
                estimated_weight = first_food.quantity
            elif first_food.quantity > 10:  # Assume grams if quantity is large
                estimated_weight = first_food.quantity

        return estimated_weight

    def _determine_meal_type(self, meal_time: datetime) -> str:
        """Determine meal type based on time of day."""
        if not meal_time:
            return "snack"

        hour = meal_time.hour
        if 5 <= hour < 11:
            return "breakfast"
        elif 11 <= hour < 16:
            return "lunch"
        elif hour >= 16 or hour < 1:
            return "dinner"
        else:
            return "snack"
