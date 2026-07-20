"""Query for one owner-scoped recommendation slot detail."""

from __future__ import annotations

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetMealRecommendationSlotDetailQuery(Query):
    """Get one durable recommendation slot with alternatives."""

    user_id: str
    plan_id: str
    slot_id: str
