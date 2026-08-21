"""Port for meal scan visual identity persistence."""

from __future__ import annotations

from typing import Protocol

from src.domain.model.meal_scan_visual_identity import MealScanVisualIdentity


class MealScanVisualIdentityRepositoryPort(Protocol):
    async def save(self, identity: MealScanVisualIdentity) -> MealScanVisualIdentity: ...

    async def list_by_user_source_dish(
        self,
        *,
        user_id: str,
        source: str,
        dish_slug: str,
        limit: int = 20,
    ) -> list[MealScanVisualIdentity]: ...

    async def find_by_identity_key(
        self,
        *,
        user_id: str,
        identity_key: str,
        source: str,
        limit: int = 5,
    ) -> list[MealScanVisualIdentity]: ...

    async def delete_by_meal_id(self, meal_id: str) -> None: ...

    async def count_for_user_source(self, *, user_id: str, source: str) -> int: ...
