"""FastAPI DI for the meal image cache services."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from src.domain.services.meal_image_cache.meal_image_cache_service import (
    MealImageCacheService,
)
from src.infra.adapters.clip_embedding_adapter import ClipEmbeddingAdapter
from src.infra.config.settings import get_settings
from src.infra.repositories.pending_meal_image_repository import (
    PendingMealImageRepository,
)
from src.infra.repositories.pgvector_meal_image_cache_repository import (
    PgvectorMealImageCacheRepository,
)
from src.api.base_dependencies import get_db


@lru_cache(maxsize=1)
def _singleton_embedder():
    settings = get_settings()
    return ClipEmbeddingAdapter.from_settings(
        model_name=settings.CLIP_MODEL_NAME,
        device=settings.CLIP_DEVICE,
        dim=settings.CLIP_EMBEDDING_DIM,
    )


async def get_meal_image_cache_service(
    session: Session = Depends(get_db),
) -> MealImageCacheService:
    settings = get_settings()
    return MealImageCacheService(
        cache=PgvectorMealImageCacheRepository(session),
        embedder=_singleton_embedder(),
        dedup_threshold=settings.TEXT_DEDUP_THRESHOLD,
    )


async def get_pending_queue(
    session: Session = Depends(get_db),
) -> PendingMealImageRepository:
    return PendingMealImageRepository(session)
