"""FastAPI DI for the meal image cache services.

The API uses GeminiTextEmbeddingAdapter for vector search — no torch, no local model.
SigLIP/torch is only used by the nightly pipeline (scripts/resolve_pending_images.py)
for image-text scoring, which requires vision encoding.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.domain.services.meal_image_cache.meal_image_cache_service import (
    MealImageCacheService,
)
from src.infra.adapters.gemini_text_embedding_adapter import get_gemini_text_embedder
from src.infra.config.settings import get_settings
from src.infra.repositories.pending_meal_image_repository import (
    PendingMealImageRepository,
)
from src.infra.repositories.pgvector_meal_image_cache_repository import (
    PgvectorMealImageCacheRepository,
)
from src.api.base_dependencies import get_db


async def get_meal_image_cache_service(
    session: Session = Depends(get_db),
) -> MealImageCacheService:
    settings = get_settings()
    return MealImageCacheService(
        cache=PgvectorMealImageCacheRepository(session),
        embedder=get_gemini_text_embedder(settings.GOOGLE_API_KEY),
        dedup_threshold=settings.TEXT_DEDUP_THRESHOLD,
    )


async def get_pending_queue(
    session: Session = Depends(get_db),
) -> PendingMealImageRepository:
    return PendingMealImageRepository(session)
