"""Embed-and-query hot path + the store helper used by the job."""

from __future__ import annotations

from typing import Optional

from src.domain.model.meal_image_cache import CachedImage, CachedImageUpsert
from src.domain.ports.embedding_service_port import EmbeddingService
from src.domain.ports.vector_cache_port import VectorCachePort
from src.domain.services.meal_image_cache.name_canonicalizer import slug


class MealImageCacheService:
    def __init__(
        self,
        cache: VectorCachePort,
        embedder: EmbeddingService,
        dedup_threshold: float,
    ):
        self._cache = cache
        self._embedder = embedder
        self._threshold = dedup_threshold

    async def lookup_batch(self, names: list[str]) -> list[Optional[CachedImage]]:
        if not names:
            return []

        embeddings = await self._embedder.embed_text(names)

        out: list[Optional[CachedImage]] = []
        for emb in embeddings:
            hit = await self._cache.query_nearest(emb)
            if hit is not None and hit.cosine >= self._threshold:
                out.append(hit)
            else:
                out.append(None)
        return out

    async def store(
        self,
        *,
        meal_name: str,
        text_embedding: list[float],
        image_url: str,
        thumbnail_url: Optional[str],
        source: str,
        confidence: Optional[float],
    ) -> None:
        await self._cache.upsert(
            CachedImageUpsert(
                meal_name=meal_name,
                name_slug=slug(meal_name),
                text_embedding=text_embedding,
                image_url=image_url,
                thumbnail_url=thumbnail_url,
                source=source,
                confidence=confidence,
            )
        )
