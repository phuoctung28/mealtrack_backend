"""Postgres-backed PendingQueuePort (synchronous SQLAlchemy session)."""

from __future__ import annotations

from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session

from src.domain.model.meal_image_cache import PendingItem
from src.infra.database.models.pending_meal_image_resolution import (
    PendingMealImageResolutionModel,
)


class PendingMealImageRepository:
    def __init__(self, session: Session):
        self._session = session

    async def enqueue_many(self, items: list[PendingItem]) -> None:
        if not items:
            return
        for item in items:
            stmt = text(
                "INSERT INTO pending_meal_image_resolution "
                "(name_slug, meal_name, candidate_image_url, candidate_thumbnail_url, candidate_source) "
                "VALUES (:name_slug, :meal_name, :candidate_image_url, "
                "        :candidate_thumbnail_url, :candidate_source) "
                "ON CONFLICT (name_slug) DO NOTHING"
            )
            self._session.execute(
                stmt,
                {
                    "name_slug": item.name_slug,
                    "meal_name": item.meal_name,
                    "candidate_image_url": item.candidate_image_url,
                    "candidate_thumbnail_url": item.candidate_thumbnail_url,
                    "candidate_source": item.candidate_source,
                },
            )
        self._session.commit()

    async def claim_batch(self, limit: int) -> list[PendingItem]:
        stmt = (
            select(PendingMealImageResolutionModel)
            .order_by(PendingMealImageResolutionModel.enqueued_at.asc())
            .limit(limit)
        )
        rows = self._session.execute(stmt).scalars().all()
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
        self._session.execute(
            delete(PendingMealImageResolutionModel).where(
                PendingMealImageResolutionModel.name_slug == name_slug
            )
        )
        self._session.commit()

    async def mark_failed(self, name_slug: str, error: str) -> None:
        self._session.execute(
            update(PendingMealImageResolutionModel)
            .where(PendingMealImageResolutionModel.name_slug == name_slug)
            .values(
                attempts=PendingMealImageResolutionModel.attempts + 1,
                last_error=error,
            )
        )
        self._session.commit()
