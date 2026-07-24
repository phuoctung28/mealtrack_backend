"""Query handler for meal recommendation plan reads."""

from __future__ import annotations

from datetime import datetime

from src.app.events.base import EventHandler, handles
from src.app.queries.meal_recommendation import GetMealRecommendationPlanQuery
from src.domain.model.meal_recommendation import PersistedMealRecommendationPlan
from src.domain.utils.timezone_utils import get_zone_info


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
            plan = await uow.meal_recommendation_plans.get_summary(
                user_id=query.user_id,
                plan_id=query.plan_id,
            )
            if plan is not None and plan.is_expired(
                datetime.now(get_zone_info(plan.timezone)).date()
            ):
                return None
            if plan is not None:
                await uow.meal_recommendation_plans.mark_shown(
                    user_id=query.user_id,
                    plan_id=query.plan_id,
                    slot_ids=tuple(slot.id for slot in plan.slots),
                )
            return plan
