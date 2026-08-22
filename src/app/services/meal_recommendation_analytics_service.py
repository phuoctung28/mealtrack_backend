"""Privacy-safe analytics for catalog meal recommendations."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Protocol

from src.domain.model.meal_recommendation import PersistedMealRecommendationPlan


class AnalyticsCapturePort(Protocol):
    async def capture(
        self,
        *,
        distinct_id: str,
        event: str,
        properties: dict[str, Any],
    ) -> None:
        """Capture one product analytics event."""


class MealRecommendationAnalyticsService:
    """Emit bounded recommendation analytics without raw user identity."""

    def __init__(self, *, salt: str, adapter: AnalyticsCapturePort | None) -> None:
        self.salt = salt
        self.adapter = adapter

    async def capture_plan_response(
        self,
        *,
        user_id: str,
        event: str,
        plan: PersistedMealRecommendationPlan,
    ) -> None:
        if not self.adapter or not self.salt:
            return
        await self.adapter.capture(
            distinct_id=_pseudonymous_id(user_id, self.salt),
            event=event,
            properties={
                "schema_version": "meal_recommendation_v1",
                "slots_count": len(plan.slots),
                "alternatives_count": sum(
                    len(slot.alternatives) for slot in plan.slots
                ),
            },
        )

    async def capture_slot_response(
        self,
        *,
        user_id: str,
        event: str,
        plan_id: str,
    ) -> None:
        if not self.adapter or not self.salt:
            return
        properties = {
            "schema_version": "meal_recommendation_v1",
            "plan_id_hash": _pseudonymous_id(plan_id, self.salt),
        }
        await self.adapter.capture(
            distinct_id=_pseudonymous_id(user_id, self.salt),
            event=event,
            properties=properties,
        )


def _pseudonymous_id(user_id: str, salt: str) -> str:
    digest = hmac.new(
        salt.encode("utf-8"),
        user_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"meal-rec-v1:{digest}"
