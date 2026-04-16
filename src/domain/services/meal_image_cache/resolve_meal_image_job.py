"""Resolve the best image for a single meal name, upsert to cache, emit event.

Flow:
  1. Already cached (cosine ≥ cache_hit_threshold)  → return early, no work.
  2. candidate_image_url present       → download + SigLIP score.
                                         Score ≥ threshold → store & return.
                                         Score < threshold → fall through to AI.
  3. candidate_image_url absent        → Pexels/Unsplash already failed at API
                                         time; skip straight to AI generation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from src.app.events.meal_suggestion.meal_image_resolved_event import (
    MealImageResolvedEvent,
)
from src.domain.model.meal_image_cache import CachedImageUpsert, PendingItem
from src.domain.services.meal_image_cache.name_canonicalizer import slug

logger = logging.getLogger(__name__)


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
        text_embedder,      # Gemini API — produces embeddings stored in pgvector
        image_scorer,       # SigLIP — scores image/text relevance via sigmoid logits
        http,               # object with `download(url) -> bytes`
        cloudinary,         # object with `save(bytes, content_type) -> url`
        ai_generator,       # Cloudflare Workers AI FLUX — fallback when no web candidate passes
        event_bus,
        image_threshold: float,
        cache_hit_threshold: float,  # cosine similarity to consider a cache hit (e.g. 0.80)
    ):
        self._cache = cache
        self._text_embedder = text_embedder
        self._image_scorer = image_scorer
        self._http = http
        self._cloudinary = cloudinary
        self._ai_generator = ai_generator
        self._event_bus = event_bus
        self._threshold = image_threshold
        self._cache_hit_threshold = cache_hit_threshold

    async def run(self, item: PendingItem) -> ResolveResult:
        meal_name = item.meal_name
        text_emb = (await self._text_embedder.embed_text([meal_name]))[0]

        existing = await self._cache.query_nearest(text_emb)
        if existing is not None and existing.cosine >= self._cache_hit_threshold:
            logger.info("already cached: %s", meal_name)
            return ResolveResult(existing.image_url, existing.source, existing.confidence)

        # Step 2: score the candidate URL recorded at API time (if any).
        if item.candidate_image_url:
            try:
                data = await self._http.download(item.candidate_image_url)
                score = await self._image_scorer.score_image_text(data, meal_name)
                logger.info(
                    "candidate score for %s: %.3f  url=%s",
                    meal_name, score, item.candidate_image_url,
                )
                if score >= self._threshold:
                    final_url = self._cloudinary.save(data, "image/jpeg")
                    result = ResolveResult(
                        final_url,
                        item.candidate_source or "external",
                        float(score),
                    )
                    await self._store(meal_name, text_emb, result, item.candidate_thumbnail_url)
                    return result
                else:
                    logger.info(
                        "candidate below threshold (%.3f < %.3f), falling back to AI",
                        score, self._threshold,
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("candidate download/score failed for %s: %s", meal_name, e)
        else:
            # Step 3: no URL recorded — web search already failed at API time.
            logger.info("no candidate URL for %s, going straight to AI", meal_name)

        # AI generation fallback.
        prompt = f"High quality food photograph of {meal_name}, overhead shot, natural lighting"
        try:
            ai_bytes = await self._ai_generator.generate(prompt)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"AI image generation failed for {meal_name}: {e}") from e

        ai_score: Optional[float] = None
        try:
            ai_score = await self._image_scorer.score_image_text(ai_bytes, meal_name)
            logger.info("ai_generated score for %s: %.3f", meal_name, ai_score)
        except Exception as e:  # noqa: BLE001
            logger.warning("could not score ai image for %s: %s", meal_name, e)

        final_url = self._cloudinary.save(ai_bytes, "image/png")
        result = ResolveResult(final_url, "ai_generated", ai_score)
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
