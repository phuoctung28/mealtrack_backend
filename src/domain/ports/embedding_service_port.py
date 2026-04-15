"""Port for CLIP-style text+image embeddings."""
from __future__ import annotations

from typing import Protocol


class EmbeddingService(Protocol):
    async def embed_text(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_image_bytes(self, data: bytes) -> list[float]: ...
