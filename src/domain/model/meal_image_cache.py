"""Domain dataclasses for the meal image cache and pending queue."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CachedImage:
    meal_name: str
    name_slug: str
    image_url: str
    thumbnail_url: str | None
    source: str
    confidence: float | None
    cosine: float


@dataclass(frozen=True)
class CachedImageUpsert:
    meal_name: str
    name_slug: str
    text_embedding: list[float]
    image_url: str
    thumbnail_url: str | None
    source: str
    confidence: float | None
    embedding_provider: str = "cloudflare-workers-ai"
    embedding_model: str = "@cf/google/embeddinggemma-300m"


@dataclass(frozen=True)
class PendingItem:
    meal_name: str
    name_slug: str
    candidate_image_url: str | None = None
    candidate_thumbnail_url: str | None = None
    candidate_source: str | None = None
    attempts: int = 0
