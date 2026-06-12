"""Postgres-backed PendingQueuePort using SQLAlchemy AsyncSession."""

from __future__ import annotations

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.meal_image_cache import PendingItem
from src.infra.database.models.pending_meal_image_resolution import (
    PendingMealImageResolutionModel,
)


class AsyncPendingMealImageRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def enqueue_many(self, items: list[PendingItem]) -> None:
        if not items:
            return

        stmt = text(
            "INSERT INTO pending_meal_image_resolution "
            "(name_slug, meal_name, candidate_image_url, candidate_thumbnail_url, candidate_source) "
            "VALUES (:name_slug, :meal_name, :candidate_image_url, "
            "        :candidate_thumbnail_url, :candidate_source) "
            "ON CONFLICT (name_slug) DO NOTHING"
        )
        for item in items:
            await self._session.execute(
                stmt,
                {
                    "name_slug": item.name_slug,
                    "meal_name": item.meal_name,
                    "candidate_image_url": item.candidate_image_url,
                    "candidate_thumbnail_url": item.candidate_thumbnail_url,
                    "candidate_source": item.candidate_source,
                },
            )
        await self._session.flush()

    async def claim_batch(self, limit: int) -> list[PendingItem]:
        stmt = (
            select(PendingMealImageResolutionModel)
            .order_by(PendingMealImageResolutionModel.enqueued_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            PendingItem(
                meal_name=r.meal_name,
                name_slug=r.name_slug,
                candidate_image_url=r.candidate_image_url,
                candidate_thumbnail_url=r.candidate_thumbnail_url,
                candidate_source=r.candidate_source,
                attempts=r.attempts,
            )
            for r in rows
        ]

    async def mark_resolved(self, name_slug: str) -> None:
        await self._session.execute(
            delete(PendingMealImageResolutionModel).where(
                PendingMealImageResolutionModel.name_slug == name_slug
            )
        )
        await self._session.flush()

    async def mark_failed(self, name_slug: str, error: str) -> None:
        await self._session.execute(
            update(PendingMealImageResolutionModel)
            .where(PendingMealImageResolutionModel.name_slug == name_slug)
            .values(
                attempts=PendingMealImageResolutionModel.attempts + 1,
                last_error=error,
            )
        )
        await self._session.flush()
