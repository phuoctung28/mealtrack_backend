"""Port for the pending-resolution queue."""

from __future__ import annotations

from typing import Protocol

from src.domain.model.meal_image_cache import PendingItem


class PendingQueuePort(Protocol):
    async def enqueue_many(self, items: list[PendingItem]) -> None: ...
    async def claim_batch(self, limit: int) -> list[PendingItem]: ...
    async def mark_resolved(self, name_slug: str) -> None: ...
    async def mark_failed(self, name_slug: str, error: str) -> None: ...
