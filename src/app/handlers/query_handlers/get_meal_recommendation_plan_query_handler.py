"""Query handler for meal recommendation plan reads."""

from __future__ import annotations

from src.app.events.base import EventHandler, handles
from src.app.queries.meal_recommendation import GetMealRecommendationPlanQuery
from src.domain.model.meal_recommendation import PersistedMealRecommendationPlan


@handles(GetMealRecommendationPlanQuery)
class GetMealRecommendationPlanQueryHandler(
    EventHandler[
        GetMealRecommendationPlanQuery,
        PersistedMealRecommendationPlan | None,
    ]
):
    """Read owner-scoped durable recommendation plans."""

    def __init__(self, uow_factory):
        self._uow_factory = uow_factory

    async def handle(
        self,
        query: GetMealRecommendationPlanQuery,
    ) -> PersistedMealRecommendationPlan | None:
        async with self._uow_factory() as uow:
            return await uow.meal_recommendation_plans.get_by_id(
                user_id=query.user_id,
                plan_id=query.plan_id,
            )
