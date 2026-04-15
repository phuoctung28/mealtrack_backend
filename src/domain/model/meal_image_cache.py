"""Domain dataclasses for the meal image cache and pending queue."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CachedImage:
    meal_name: str
    name_slug: str
    image_url: str
    thumbnail_url: Optional[str]
    source: str
    confidence: Optional[float]
    cosine: float


@dataclass(frozen=True)
class CachedImageUpsert:
    meal_name: str
    name_slug: str
    text_embedding: list[float]
    image_url: str
    thumbnail_url: Optional[str]
    source: str
    confidence: Optional[float]


@dataclass(frozen=True)
class PendingItem:
    meal_name: str
    name_slug: str
    candidate_image_url: Optional[str] = None
    candidate_thumbnail_url: Optional[str] = None
    candidate_source: Optional[str] = None
    attempts: int = 0
