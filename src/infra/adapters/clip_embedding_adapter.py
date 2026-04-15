"""
Multilingual CLIP adapter. Lazy-loads the model once per process.
"""
from __future__ import annotations

import asyncio
import io
import logging

logger = logging.getLogger(__name__)

_model_singleton = None


def load_clip_model(model_name: str, device: str):
    global _model_singleton
    if _model_singleton is None:
        from sentence_transformers import SentenceTransformer  # lazy
        logger.info("loading CLIP model %s on %s", model_name, device)
        _model_singleton = SentenceTransformer(model_name, device=device)
    return _model_singleton


class ClipEmbeddingAdapter:
    def __init__(self, model, dim: int = 512):
        self._model = model
        self._dim = dim

    @classmethod
    def from_settings(cls, model_name: str, device: str, dim: int):
        return cls(model=load_clip_model(model_name, device), dim=dim)

    async def embed_text(self, texts: list[str]) -> list[list[float]]:
        def _run():
            vecs = self._model.encode(
                texts, convert_to_numpy=True, normalize_embeddings=True,
            )
            return [v.tolist() for v in vecs]
        return await asyncio.to_thread(_run)

    async def embed_image_bytes(self, data: bytes) -> list[float]:
        def _run():
            from PIL import Image  # lazy
            img = Image.open(io.BytesIO(data)).convert("RGB")
            vec = self._model.encode(
                [img], convert_to_numpy=True, normalize_embeddings=True,
            )[0]
            return vec.tolist()
        return await asyncio.to_thread(_run)
