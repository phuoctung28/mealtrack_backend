"""Handler for bulk activities query — returns activities grouped by date."""

import logging
from typing import Dict, List, Any, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.activity.get_bulk_activities_query import GetBulkActivitiesQuery
from src.domain.model.meal import Meal, MealStatus
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
from src.infra.repositories.meal_repository import MealProjection

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = {MealStatus.READY, MealStatus.ENRICHING}


def _build_meal_activity(meal: Meal, language: str = "en") -> Dict[str, Any]:
    title = meal.dish_name or "Unknown Meal"
    if language and language != "en" and meal.translations:
        translation = meal.translations.get(language)
        if translation and translation.dish_name:
            title = translation.dish_name

    image_url = meal.image.url if meal.image else None
    return {
        "id": meal.meal_id,
        "type": "meal",
        "timestamp": format_iso_utc(meal.created_at),
        "title": title,
        "emoji": meal.emoji,
        "meal_type": meal.meal_type,
        "calories": round(meal.nutrition.calories, 1) if meal.nutrition else 0,
        "macros": {
            "protein": round(meal.nutrition.macros.protein, 1) if meal.nutrition else 0,
            "carbs": round(meal.nutrition.macros.carbs, 1) if meal.nutrition else 0,
            "fat": round(meal.nutrition.macros.fat, 1) if meal.nutrition else 0,
        },
        "quantity": meal.quantity,
        "status": meal.status.value if meal.status else "unknown",
        "image_url": image_url,
        "source": meal.source,
    }


def _build_hydration_activity(meal: Meal, language: str = "en") -> Dict[str, Any]:
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
        "title": localized_name_for_catalog_name(meal.dish_name, language) or "Water",
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


@handles(GetBulkActivitiesQuery)
class GetBulkActivitiesQueryHandler(
    EventHandler[GetBulkActivitiesQuery, Dict[str, List[Dict[str, Any]]]]
):
    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(
        self, query: GetBulkActivitiesQuery
    ) -> Dict[str, List[Dict[str, Any]]]:
        async with AsyncUnitOfWork() as uow:
            user_tz_str = await resolve_user_timezone_async(
                query.user_id, uow, query.header_timezone
            )
            tz = get_zone_info(user_tz_str)

            meals = await uow.meals.find_by_date_range(
                user_id=query.user_id,
                start_date=query.start_date,
                end_date=query.end_date,
                user_timezone=user_tz_str,
                projection=MealProjection.FULL_WITH_TRANSLATIONS,
            )

        language = query.language or "en"
        result: Dict[str, List[Dict[str, Any]]] = {}

        for meal in meals:
            if meal.status not in _ACTIVE_STATUSES:
                continue
            local_date = meal.created_at.astimezone(tz).date().isoformat()
            if local_date not in result:
                result[local_date] = []
            if meal.meal_type == "hydration":
                result[local_date].append(_build_hydration_activity(meal, language))
            else:
                result[local_date].append(_build_meal_activity(meal, language))

        return result
