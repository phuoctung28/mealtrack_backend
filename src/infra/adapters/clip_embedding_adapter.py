"""
Multilingual CLIP adapter. Lazy-loads the model once per process.

Architecture note
-----------------
clip-ViT-B-32-multilingual-v1 uses an XLM-RoBERTa text backbone — it does NOT
support image inputs via SentenceTransformer.encode().  For images the model
card recommends using the original clip-ViT-B-32, whose image embeddings are in
the same 512-d space.  We therefore keep two singletons:

  _text_model_singleton  — multilingual CLIP for text
  _image_model_singleton — clip-ViT-B-32 for images
"""

from __future__ import annotations

import asyncio
import io
import logging

logger = logging.getLogger(__name__)

_IMAGE_MODEL_NAME = "sentence-transformers/clip-ViT-B-32"

_text_model_singleton = None
_image_model_singleton = None


def load_clip_model(model_name: str, device: str):
    global _text_model_singleton
    if _text_model_singleton is None:
        from sentence_transformers import SentenceTransformer  # lazy

        logger.info("loading CLIP text model %s on %s", model_name, device)
        _text_model_singleton = SentenceTransformer(model_name, device=device)
    return _text_model_singleton


def _load_image_model(device: str):
    global _image_model_singleton
    if _image_model_singleton is None:
        from sentence_transformers import SentenceTransformer  # lazy

        logger.info("loading CLIP image model %s on %s", _IMAGE_MODEL_NAME, device)
        _image_model_singleton = SentenceTransformer(_IMAGE_MODEL_NAME, device=device)
    return _image_model_singleton


class ClipEmbeddingAdapter:
    def __init__(self, text_model, image_model, dim: int = 512):
        self._text_model = text_model
        self._image_model = image_model
        self._dim = dim

    @classmethod
    def from_settings(cls, model_name: str, device: str, dim: int):
        return cls(
            text_model=load_clip_model(model_name, device),
            image_model=_load_image_model(device),
            dim=dim,
        )

    async def embed_text(self, texts: list[str]) -> list[list[float]]:
        def _run():
            vecs = self._text_model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            return [v.tolist() for v in vecs]

        return await asyncio.to_thread(_run)

    async def embed_image_bytes(self, data: bytes) -> list[float]:
        def _run():
            from PIL import Image  # lazy

            img = Image.open(io.BytesIO(data)).convert("RGB")
            # clip-ViT-B-32 uses CLIPModel which handles PIL Image inputs.
            vec = self._image_model.encode(
                [img],
                convert_to_numpy=True,
                normalize_embeddings=True,
            )[0]
            return vec.tolist()

        return await asyncio.to_thread(_run)
