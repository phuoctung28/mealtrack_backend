"""Project linked meal history into recommendation affinity inputs."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from src.domain.model.meal_projection import MealProjection
from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientAffinityProfile,
    IngredientAffinityService,
    IngredientHistoryEvent,
)

_HISTORY_DAYS = 90
_HISTORY_LIMIT = 5000


class MealRecommendationHistoryProjector:
    """Build ingredient affinity from recently logged linked food references."""

    def __init__(self, affinity_service: IngredientAffinityService | None = None):
        self._affinity_service = affinity_service or IngredientAffinityService()

    async def build_affinity(
        self,
        uow: Any,
        *,
        user_id: str,
        start_date: date,
        timezone: str,
    ) -> IngredientAffinityProfile:
        history_start = start_date - timedelta(days=_HISTORY_DAYS)
        history_end = start_date - timedelta(days=1)
        meals = await uow.meals.find_by_date_range(
            user_id=user_id,
            start_date=history_start,
            end_date=history_end,
            limit=_HISTORY_LIMIT,
            user_timezone=timezone,
            projection=MealProjection.MACROS_ONLY,
        )
        events: list[IngredientHistoryEvent] = []
        for meal in meals:
            nutrition = getattr(meal, "nutrition", None)
            if not nutrition or not nutrition.food_items:
                continue
            occurred_at = meal.ready_at or meal.created_at
            for item in nutrition.food_items:
                if item.food_reference_id is None:
                    continue
                events.append(
                    IngredientHistoryEvent(
                        food_reference_id=item.food_reference_id,
                        eaten_at=occurred_at,
                        grams=float(item.quantity),
                    )
                )
        return self._affinity_service.build_profile(
            events,
            now=datetime.combine(start_date, time.min, tzinfo=UTC),
        )
