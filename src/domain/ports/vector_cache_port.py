"""Port for the meal image vector cache."""
from __future__ import annotations

from typing import Optional, Protocol

from src.domain.model.meal_image_cache import CachedImage, CachedImageUpsert


class VectorCachePort(Protocol):
    async def query_nearest(self, text_embedding: list[float]) -> Optional[CachedImage]: ...
    async def upsert(self, record: CachedImageUpsert) -> None: ...
