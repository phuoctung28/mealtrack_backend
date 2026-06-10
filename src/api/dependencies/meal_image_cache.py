"""FastAPI DI for the meal image cache services.

The API uses GeminiTextEmbeddingAdapter for vector search — no torch, no local model.
SigLIP/torch is only used by the nightly pipeline (scripts/resolve_pending_images.py)
for image-text scoring, which requires vision encoding.
"""

from __future__ import annotations

import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.meal_image_cache import PendingItem
from src.domain.services.meal_image_cache.meal_image_cache_service import (
    MealImageCacheService,
)
from src.infra.adapters.gemini_text_embedding_adapter import get_gemini_text_embedder
from src.infra.config.settings import get_settings
from src.infra.database.config_async import get_async_db
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.pending_meal_image_repository_async import (
    AsyncPendingMealImageRepository,
)
from src.infra.repositories.pgvector_meal_image_cache_repository_async import (
    AsyncPgvectorMealImageCacheRepository,
)

logger = logging.getLogger(__name__)


async def get_meal_image_cache_service(
    session: AsyncSession = Depends(get_async_db),
) -> MealImageCacheService:
    settings = get_settings()
    return MealImageCacheService(
        cache=AsyncPgvectorMealImageCacheRepository(session),
        embedder=get_gemini_text_embedder(settings.GOOGLE_API_KEY),
        dedup_threshold=settings.TEXT_DEDUP_THRESHOLD,
    )


async def get_pending_queue(
    session: AsyncSession = Depends(get_async_db),
) -> AsyncPendingMealImageRepository:
    return AsyncPendingMealImageRepository(session)


async def enqueue_pending_images(items: list[PendingItem]) -> None:
    """Enqueue pending image items in their own UoW transaction (non-fatal)."""
    if not items:
        return
    try:
        async with AsyncUnitOfWork() as uow:
            await AsyncPendingMealImageRepository(uow.session).enqueue_many(items)
    except Exception as e:
        logger.warning("Pending image queue enqueue failed (non-fatal): %s", e)
