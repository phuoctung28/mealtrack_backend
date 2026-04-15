"""Ports for embedding services.

TextEmbeddingService — text-only, no torch required. Implemented by
GeminiTextEmbeddingAdapter (API + pipeline text side).

EmbeddingService — full multimodal (text + image scoring). Implemented by
ClipEmbeddingAdapter (pipeline image-validation side only).
"""

from __future__ import annotations

from typing import Protocol


class TextEmbeddingService(Protocol):
    """Embed text to float vectors. No image encoding, no torch required."""

    async def embed_text(self, texts: list[str]) -> list[list[float]]: ...


class EmbeddingService(TextEmbeddingService, Protocol):
    """Full multimodal: text embedding + image-text scoring (requires torch/SigLIP)."""

    async def embed_image_bytes(self, data: bytes) -> list[float]: ...
    async def score_image_text(self, image_data: bytes, text: str) -> float: ...
