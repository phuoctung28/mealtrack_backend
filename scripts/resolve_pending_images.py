"""
Nightly cron entry point. Drains the pending_meal_image_resolution queue,
running ResolveMealImageJob per row.

Invoked by .github/workflows/meal-image-resolver.yml as:
    python scripts/resolve_pending_images.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.domain.services.meal_image_cache.resolve_meal_image_job import (
    ResolveMealImageJob,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)


async def drain(
    *,
    pending_repo,
    cache_repo,
    text_embedder,
    image_scorer,
    image_search,
    http,
    cloudinary,
    ai_primary,
    ai_fallback,
    event_bus,
    image_threshold: float,
    max_jobs: int,
    inter_call_delay: float,
    max_attempts: int,
) -> dict:
    """Returns a summary dict of the run."""
    items = await pending_repo.claim_batch(max_jobs)
    if not items:
        logger.info("drain: no pending items")
        return {
            "processed": 0,
            "matched": 0,
            "ai_generated": 0,
            "failed": 0,
            "skipped": 0,
        }

    logger.info("drain: %d items to process", len(items))

    job = ResolveMealImageJob(
        cache=cache_repo,
        text_embedder=text_embedder,
        image_scorer=image_scorer,
        image_search=image_search,
        http=http,
        cloudinary=cloudinary,
        ai_primary=ai_primary,
        ai_fallback=ai_fallback,
        event_bus=event_bus,
        image_threshold=image_threshold,
    )

    summary = {
        "processed": 0,
        "matched": 0,
        "ai_generated": 0,
        "failed": 0,
        "skipped": 0,
    }
    for i, item in enumerate(items):
        if item.attempts >= max_attempts:
            logger.warning("skipping %s — exceeded max_attempts", item.name_slug)
            summary["skipped"] += 1
            continue
        try:
            result = await job.run(item)
            await pending_repo.mark_resolved(item.name_slug)
            summary["processed"] += 1
            if result.source == "ai_generated":
                summary["ai_generated"] += 1
            else:
                summary["matched"] += 1
        except Exception as e:  # noqa: BLE001
            logger.exception("failed %s", item.name_slug)
            await pending_repo.mark_failed(item.name_slug, str(e)[:500])
            summary["failed"] += 1

        if i < len(items) - 1 and inter_call_delay > 0:
            await asyncio.sleep(inter_call_delay)

    logger.info("drain summary: %s", summary)
    return summary


async def _main() -> int:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import httpx

    from src.infra.config.settings import get_settings
    from src.infra.database.config import SQLALCHEMY_DATABASE_URL
    from src.infra.adapters.clip_embedding_adapter import ClipEmbeddingAdapter
    from src.infra.adapters.gemini_text_embedding_adapter import GeminiTextEmbeddingAdapter
    from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
    from src.infra.adapters.pollinations_image_generator import (
        PollinationsImageGenerator,
    )
    from src.infra.adapters.imagen_image_generator import ImagenImageGenerator
    from src.infra.repositories.pending_meal_image_repository import (
        PendingMealImageRepository,
    )
    from src.infra.repositories.pgvector_meal_image_cache_repository import (
        PgvectorMealImageCacheRepository,
    )
    from src.api.dependencies.food_image import get_food_image_service
    from src.infra.event_bus import PyMediatorEventBus

    settings = get_settings()

    engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    class _HttpDownloader:
        async def download(self, url):
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
                r = await c.get(url)
                r.raise_for_status()
                return r.content

    class _ImageSearchWrapper:
        def __init__(self, svc):
            self._svc = svc

        async def fetch_candidates(self, name):
            result = await self._svc.search_food_image(name)
            if result is None:
                return []
            return [
                {
                    "url": result.url,
                    "thumbnail_url": result.thumbnail_url,
                    "source": result.source,
                }
            ]

    # Gemini: text embedding for storing/querying pgvector (consistent with API)
    text_embedder = GeminiTextEmbeddingAdapter(api_key=settings.GOOGLE_API_KEY)

    # SigLIP: image-text scoring only (validates candidate images, requires torch)
    image_scorer = ClipEmbeddingAdapter.from_settings(
        model_name=settings.CLIP_MODEL_NAME,
        device=settings.CLIP_DEVICE,
        dim=settings.CLIP_EMBEDDING_DIM,
    )

    with SessionLocal() as session:
        summary = await drain(
            pending_repo=PendingMealImageRepository(session),
            cache_repo=PgvectorMealImageCacheRepository(session),
            text_embedder=text_embedder,
            image_scorer=image_scorer,
            image_search=_ImageSearchWrapper(get_food_image_service()),
            http=_HttpDownloader(),
            cloudinary=CloudinaryImageStore(),
            ai_primary=PollinationsImageGenerator(
                base_url=settings.POLLINATIONS_BASE_URL,
                timeout=settings.AI_IMAGE_TIMEOUT_SECONDS,
            ),
            ai_fallback=ImagenImageGenerator(
                api_key=settings.GOOGLE_API_KEY or "",
                timeout=settings.AI_IMAGE_TIMEOUT_SECONDS,
            ),
            event_bus=PyMediatorEventBus(),
            image_threshold=settings.IMAGE_MATCH_THRESHOLD,
            max_jobs=settings.MAX_JOBS_PER_CRON,
            inter_call_delay=settings.CRON_EXTERNAL_CALL_DELAY_SECONDS,
            max_attempts=settings.MAX_RESOLUTION_ATTEMPTS,
        )

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
