"""FastAPI DI for the meal image cache services.

The API uses OpenAI text embeddings for vector search — no torch, no local model.
SigLIP/torch is only used by the nightly pipeline (scripts/resolve_pending_images.py)
for image-text scoring, which requires vision encoding.
"""

from __future__ import annotations

from importlib import import_module

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.services.meal_image_cache.meal_image_cache_service import (
    MealImageCacheService,
)
from src.infra.config.settings import get_settings
from src.infra.database.config_async import get_async_db
from src.infra.repositories.pending_meal_image_repository_async import (
    AsyncPendingMealImageRepository,
)
from src.infra.repositories.pgvector_meal_image_cache_repository_async import (
    AsyncPgvectorMealImageCacheRepository,
)
from src.infra.services.pending_image_enqueue_service import enqueue_pending_images

__all__ = [
    "get_meal_image_cache_service",
    "get_pending_queue",
    "enqueue_pending_images",
]


def get_openai_text_embedder(api_key: str, model: str, dimensions: int):
    module = import_module("src.infra.adapters.openai_text_embedding_adapter")
    return module.get_openai_text_embedder(api_key, model, dimensions)


async def get_meal_image_cache_service(
    session: AsyncSession = Depends(get_async_db),
) -> MealImageCacheService:
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for meal image cache embeddings")

    return MealImageCacheService(
        cache=AsyncPgvectorMealImageCacheRepository(session),
        embedder=get_openai_text_embedder(
            settings.OPENAI_API_KEY,
            settings.OPENAI_EMBEDDING_MODEL,
            settings.OPENAI_EMBEDDING_DIMENSIONS,
        ),
        dedup_threshold=settings.TEXT_DEDUP_THRESHOLD,
    )


async def get_pending_queue(
    session: AsyncSession = Depends(get_async_db),
) -> AsyncPendingMealImageRepository:
    return AsyncPendingMealImageRepository(session)
