"""Durable meal recommendation candidate-row aggregate snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from src.domain.model.meal_recommendation.catalog_recipe import CatalogMeal


@dataclass(frozen=True)
class PersistedMealRecommendationCandidate:
    """Persisted candidate snapshot for one logical slot."""

    id: str
    slot_id: str
    recommendation_date: date
    meal_type: str
    catalog_meal_id: str
    candidate_rank: int
    is_selected: bool
    score: Decimal
    selection_version: int
    catalog_meal: CatalogMeal | None = None
    logged_at: datetime | None = None
    logged_meal_id: str | None = None


@dataclass(frozen=True)
class PersistedMealRecommendationSlot:
    """Selected candidate plus alternatives for one recommendation slot."""

    id: str
    slot_date: date
    day_index: int
    meal_type: str
    catalog_meal_id: str
    target_calories: int
    score: float
    position: int
    selection_version: int = 1
    logged_meal_id: str | None = None
    selected: PersistedMealRecommendationCandidate | None = None
    alternatives: tuple[PersistedMealRecommendationCandidate, ...] = ()

    @property
    def version(self) -> int:
        """Temporary API compatibility for selection_version."""

        return self.selection_version


@dataclass(frozen=True)
class PersistedMealRecommendationPlan:
    """Owner-scoped durable recommendation aggregate."""

    id: str
    user_id: str
    status: str
    timezone: str
    start_date: date
    daily_calories: int
    operation: str
    idempotency_key: str
    request_fingerprint: str
    slots: tuple[PersistedMealRecommendationSlot, ...] = field(default_factory=tuple)
    created_at: datetime | None = None


@dataclass(frozen=True)
class PersistedMealRecommendationSlotMutationResult:
    """Changed-slot result for recommendation swap/log mutations."""

    plan_id: str
    user_id: str
    slot: PersistedMealRecommendationSlot
