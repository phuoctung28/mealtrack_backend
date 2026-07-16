"""Durable meal recommendation plan aggregate snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class PersistedMealRecommendationAlternative:
    """Persisted alternative recipe snapshot for one slot."""

    id: str
    recipe_version_id: str
    target_calories: int
    score: float
    position: int


@dataclass(frozen=True)
class PersistedMealRecommendationSlot:
    """Persisted selected recipe snapshot."""

    id: str
    slot_date: date
    day_index: int
    meal_type: str
    recipe_version_id: str
    target_calories: int
    score: float
    position: int
    version: int = 1
    logged_meal_id: str | None = None
    alternatives: tuple[PersistedMealRecommendationAlternative, ...] = ()


@dataclass(frozen=True)
class PersistedMealRecommendationPlan:
    """Owner-scoped durable meal recommendation aggregate."""

    id: str
    user_id: str
    status: str
    timezone: str
    start_date: date
    daily_calories: int
    algorithm_version: str
    catalog_release_id: str
    allergy_evaluated: bool
    operation: str
    idempotency_key: str
    request_fingerprint: str
    slots: tuple[PersistedMealRecommendationSlot, ...] = field(default_factory=tuple)
    created_at: datetime | None = None
