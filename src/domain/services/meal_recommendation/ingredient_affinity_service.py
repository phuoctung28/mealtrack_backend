"""Owner-scoped ingredient affinity from canonical linked history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class IngredientHistoryEvent:
    """Reduced canonical ingredient usage event for recommendation scoring."""

    food_reference_id: int
    eaten_at: datetime
    grams: float


@dataclass(frozen=True)
class IngredientAffinityProfile:
    """Normalized 90-day ingredient affinity weights."""

    weights: dict[int, float]
    confidence: float


class IngredientAffinityService:
    """Build affinity using only linked canonical ingredient IDs."""

    def build_profile(
        self,
        history: list[IngredientHistoryEvent],
        *,
        now: datetime,
    ) -> IngredientAffinityProfile:
        now_utc = _as_utc(now)
        cutoff = now_utc - timedelta(days=90)
        weighted: dict[int, float] = {}
        total = 0.0

        for event in sorted(history, key=lambda item: item.eaten_at, reverse=True):
            event_time = _as_utc(event.eaten_at)
            if event.food_reference_id <= 0 or event.grams <= 0 or event_time < cutoff:
                continue
            age_days = max((now_utc - event_time).days, 0)
            recency_weight = max(0.1, 1.0 - (age_days / 90))
            value = min(event.grams, 500.0) / 100.0 * recency_weight
            weighted[event.food_reference_id] = (
                weighted.get(event.food_reference_id, 0.0) + value
            )
            total += value

        if total <= 0:
            return IngredientAffinityProfile(weights={}, confidence=0.0)

        normalized = {
            food_reference_id: value / total
            for food_reference_id, value in weighted.items()
        }
        confidence = min(1.0, total / 25.0)
        return IngredientAffinityProfile(weights=normalized, confidence=confidence)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
