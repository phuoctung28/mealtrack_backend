"""Repository port for durable meal recommendation plans."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.model.meal_recommendation import (
    MealRecommendationAlternative,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
    PersistedMealRecommendationSlotMutationResult,
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
    async def get_summary(
        self,
        *,
        user_id: str,
        plan_id: str,
    ) -> PersistedMealRecommendationPlan | None:
        """Return selected owner-scoped slots without alternatives."""

    @abstractmethod
    async def get_slot_detail(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
    ) -> PersistedMealRecommendationSlot | None:
        """Return one owner-scoped hydrated slot with alternatives."""

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
        replenishment_alternatives: tuple[MealRecommendationAlternative, ...] = (),
    ) -> PersistedMealRecommendationSlotMutationResult:
        """Swap one owned slot and return the changed slot."""

    async def get_slot_replenishment_context(
        self, *, user_id: str, plan_id: str, slot_id: str
    ) -> (
        tuple[
            PersistedMealRecommendationSlot,
            frozenset[str],
            frozenset[str],
            str,
        ]
        | None
    ):
        """Return target slot, seen target candidates, and other selected IDs."""
        return None

    @abstractmethod
    async def mark_shown(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_ids: tuple[str, ...],
    ) -> None:
        """Persist first-shown timestamps for selected owner-scoped slots."""

    @abstractmethod
    async def skip_slot(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
    ) -> PersistedMealRecommendationSlotMutationResult:
        """Skip one owned slot and return the changed slot."""

    @abstractmethod
    async def claim_slot_log(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
    ) -> tuple[
        PersistedMealRecommendationPlan,
        PersistedMealRecommendationSlot,
        bool,
    ]:
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
    ) -> PersistedMealRecommendationSlotMutationResult:
        """Attach a materialized meal to a claimed slot log and return the slot."""

    async def clear_links_for_deleted_meal(self, *, meal_id: str) -> None:
        """Clear recommendation links before a normal meal is hard-deleted.

        Default no-op for lightweight fakes; production repos must implement.
        """
        return None

    async def find_logable_slot_for_catalog_meal(
        self,
        *,
        user_id: str,
        catalog_meal_id: str,
        slot_date,
        meal_type: str,
    ) -> tuple[str, str] | None:
        """Return (plan_id, slot_id) for a selected unlogged slot, or None."""
        return None

    async def find_active_plan_id(self, *, user_id: str) -> str | None:
        """Return the owner's active plan id, if any."""
        return None
