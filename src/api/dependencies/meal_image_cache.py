"""FastAPI DI for the meal image cache services.

The API uses Cloudflare Workers AI text embeddings for vector search — no torch,
no local model. SigLIP/torch is only used by the nightly pipeline
(scripts/resolve_pending_images.py) for image-text scoring, which requires
vision encoding.
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


def get_cloudflare_text_embedder(
    account_id: str,
    api_token: str,
    model: str,
    dimensions: int,
    timeout_seconds: int,
):
    module = import_module("src.infra.adapters.cloudflare_text_embedding_adapter")
    return module.get_cloudflare_text_embedder(
        account_id,
        api_token,
        model,
        dimensions,
        timeout_seconds,
    )


async def get_meal_image_cache_service(
    session: AsyncSession = Depends(get_async_db),
) -> MealImageCacheService:
    settings = get_settings()
    if not settings.CLOUDFLARE_ACCOUNT_ID or not settings.CLOUDFLARE_API_TOKEN:
        raise RuntimeError(
            "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required for meal image cache embeddings"
        )

    return MealImageCacheService(
        cache=AsyncPgvectorMealImageCacheRepository(session),
        embedder=get_cloudflare_text_embedder(
            settings.CLOUDFLARE_ACCOUNT_ID,
            settings.CLOUDFLARE_API_TOKEN,
            settings.CLOUDFLARE_WORKERS_AI_EMBEDDING_MODEL,
            settings.CLOUDFLARE_WORKERS_AI_EMBEDDING_DIMENSIONS,
            settings.CLOUDFLARE_WORKERS_AI_TIMEOUT_SECONDS,
        ),
        dedup_threshold=settings.TEXT_DEDUP_THRESHOLD,
    )


async def get_pending_queue(
    session: AsyncSession = Depends(get_async_db),
) -> AsyncPendingMealImageRepository:
    return AsyncPendingMealImageRepository(session)
