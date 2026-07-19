"""Query handler for meal recommendation slot detail reads."""

from __future__ import annotations

from src.app.events.base import EventHandler, handles
from src.app.queries.meal_recommendation import GetMealRecommendationSlotDetailQuery
from src.domain.model.meal_recommendation import PersistedMealRecommendationSlot


@handles(GetMealRecommendationSlotDetailQuery)
class GetMealRecommendationSlotDetailQueryHandler(
    EventHandler[
        GetMealRecommendationSlotDetailQuery,
        PersistedMealRecommendationSlot | None,
    ]
):
    """Read one owner-scoped durable recommendation slot."""

    def __init__(self, uow_factory):
        self._uow_factory = uow_factory

    async def handle(
        self,
        query: GetMealRecommendationSlotDetailQuery,
    ) -> PersistedMealRecommendationSlot | None:
        async with self._uow_factory() as uow:
            return await uow.meal_recommendation_plans.get_slot_detail(
                user_id=query.user_id,
                plan_id=query.plan_id,
                slot_id=query.slot_id,
            )
