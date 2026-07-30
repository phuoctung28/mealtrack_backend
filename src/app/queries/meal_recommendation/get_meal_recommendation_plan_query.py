"""Query for owner-scoped meal recommendation plan reads."""

from __future__ import annotations

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetMealRecommendationPlanQuery(Query):
    """Get one durable recommendation plan."""

    user_id: str
    plan_id: str
