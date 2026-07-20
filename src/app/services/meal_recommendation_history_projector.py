"""Project linked meal history into recommendation affinity inputs."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientAffinityProfile,
    IngredientAffinityService,
)

_HISTORY_DAYS = 90


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
        buckets = await uow.meals.aggregate_linked_ingredient_history(
            user_id=user_id,
            start_date=history_start,
            end_date=history_end,
            user_timezone=timezone,
            reference_date=start_date,
        )
        return self._affinity_service.build_profile_from_buckets(buckets)
