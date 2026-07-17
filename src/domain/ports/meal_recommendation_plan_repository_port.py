"""Repository port for durable meal recommendation plans."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.model.meal_recommendation import (
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)


class MealRecommendationPlanRepositoryPort(ABC):
    """Persistence contract for owner-scoped recommendation plans."""

    @abstractmethod
    async def get_by_id(
        self,
        *,
        user_id: str,
        plan_id: str,
    ) -> PersistedMealRecommendationPlan | None:
        """Return an owner-scoped plan by ID."""

    @abstractmethod
    async def get_by_idempotency_key(
        self,
        *,
        user_id: str,
        operation: str,
        idempotency_key: str,
    ) -> PersistedMealRecommendationPlan | None:
        """Return a prior request result for idempotency replay."""

    @abstractmethod
    async def lock_generation_for_user(self, *, user_id: str) -> None:
        """Serialize durable recommendation generation for one owner."""

    @abstractmethod
    async def save_new_active_plan(
        self,
        plan: PersistedMealRecommendationPlan,
    ) -> PersistedMealRecommendationPlan:
        """Supersede prior active plan and persist a new complete aggregate."""

    @abstractmethod
    async def swap_slot(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
        expected_version: int,
        alternative_catalog_meal_id: str | None,
        reason: str,
    ) -> PersistedMealRecommendationPlan:
        """Swap one owned slot and return the updated plan."""

    @abstractmethod
    async def claim_slot_log(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
    ) -> tuple[PersistedMealRecommendationPlan, PersistedMealRecommendationSlot, bool]:
        """Claim a slot log request before materializing a normal meal."""

    @abstractmethod
    async def finalize_slot_logged(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
        meal_id: str,
    ) -> PersistedMealRecommendationPlan:
        """Attach a materialized meal to a claimed slot log and return the plan."""
