"""Resolve the best image for a single meal name, upsert to cache, emit event."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional

from src.app.events.meal_suggestion.meal_image_resolved_event import (
    MealImageResolvedEvent,
)
from src.domain.model.meal_image_cache import CachedImageUpsert, PendingItem
from src.domain.services.meal_image_cache.name_canonicalizer import slug

logger = logging.getLogger(__name__)


def cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


@dataclass(frozen=True)
class ResolveResult:
    image_url: str
    source: str
    confidence: Optional[float]


class ResolveMealImageJob:
    def __init__(
        self,
        *,
        cache,
        embedder,
        image_search,  # object with `fetch_candidates(name) -> list[dict]`
        http,  # object with `download(url) -> bytes`
        cloudinary,  # object with `save(bytes, content_type) -> url`
        ai_primary,
        ai_fallback,
        event_bus,
        image_threshold: float,
    ):
        self._cache = cache
        self._embedder = embedder
        self._image_search = image_search
        self._http = http
        self._cloudinary = cloudinary
        self._ai_primary = ai_primary
        self._ai_fallback = ai_fallback
        self._event_bus = event_bus
        self._threshold = image_threshold

    async def run(self, item: PendingItem) -> ResolveResult:
        meal_name = item.meal_name
        text_emb = (await self._embedder.embed_text([meal_name]))[0]

        existing = await self._cache.query_nearest(text_emb)
        if existing is not None and existing.cosine >= 0.999:
            logger.info("already cached: %s", meal_name)
            return ResolveResult(
                existing.image_url, existing.source, existing.confidence
            )

        # Prefer the candidate URL the API already picked on miss.
        # Only call FoodImageSearchService when no URL was recorded.
        if item.candidate_image_url:
            candidates = [
                {
                    "url": item.candidate_image_url,
                    "thumbnail_url": item.candidate_thumbnail_url,
                    "source": item.candidate_source or "external",
                }
            ]
        else:
            candidates = await self._image_search.fetch_candidates(meal_name)

        best = None
        for cand in candidates:
            try:
                data = await self._http.download(cand["url"])
                img_emb = await self._embedder.embed_image_bytes(data)
                score = cosine_sim(text_emb, img_emb)
                if best is None or score > best["score"]:
                    best = {**cand, "bytes": data, "score": score}
            except Exception as e:  # noqa: BLE001
                logger.warning("candidate %s failed: %s", cand.get("url"), e)

        if best and best["score"] >= self._threshold:
            final_url = self._cloudinary.save(best["bytes"], "image/jpeg")
            result = ResolveResult(final_url, best["source"], float(best["score"]))
            await self._store(meal_name, text_emb, result, best.get("thumbnail_url"))
            return result

        prompt = f"High quality food photograph of {meal_name}, overhead shot, natural lighting"
        ai_bytes: Optional[bytes] = None
        last_error: Optional[Exception] = None
        for gen in (self._ai_primary, self._ai_fallback):
            try:
                ai_bytes = await gen.generate(prompt)
                break
            except Exception as e:  # noqa: BLE001
                logger.warning("%s failed: %s", gen.name, e)
                last_error = e

        if ai_bytes is None:
            raise RuntimeError(
                f"all image generators failed for {meal_name}: {last_error}"
            )

        final_url = self._cloudinary.save(ai_bytes, "image/png")
        result = ResolveResult(final_url, "ai_generated", None)
        await self._store(meal_name, text_emb, result, thumbnail_url=None)
        return result

    async def _store(self, meal_name, text_emb, result, thumbnail_url):
        await self._cache.upsert(
            CachedImageUpsert(
                meal_name=meal_name,
                name_slug=slug(meal_name),
                text_embedding=text_emb,
                image_url=result.image_url,
                thumbnail_url=thumbnail_url,
                source=result.source,
                confidence=result.confidence,
            )
        )
        await self._event_bus.publish(
            MealImageResolvedEvent(
                aggregate_id=slug(meal_name),
                meal_name=meal_name,
                image_url=result.image_url,
                source=result.source,
                confidence=result.confidence,
            )
        )
