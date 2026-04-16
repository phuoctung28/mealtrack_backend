"""
Text embedding adapter backed by Google Gemini's text-embedding-004 model.

Implements TextEmbeddingService — no torch, no transformers, no local model.
Uses langchain_google_genai.GoogleGenerativeAIEmbeddings which is already
installed as a dependency of langchain-google-genai.

Used by:
  - API:      MealImageCacheService.lookup_batch() → pgvector ANN query
  - Pipeline: ResolveMealImageJob.embed_text() → store text embedding in cache

The SigLIP/torch model (ClipEmbeddingAdapter) stays in the pipeline only for
image-text similarity scoring (score_image_text), which requires vision encoding.
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# Per LangChain docs: https://docs.langchain.com/oss/python/integrations/embeddings/google_generative_ai
# Use a single, explicitly supported model ID.
_GEMINI_EMBEDDING_MODEL = "gemini-embedding-2-preview"
_OUTPUT_DIM = 768  # matches the pgvector column definition (Vector(768))


class GeminiTextEmbeddingAdapter:
    """
    Wraps GoogleGenerativeAIEmbeddings for async use.

    task_type="semantic_similarity" is symmetric — the same adapter works for
    both storing (pipeline) and querying (API) without separate instances.
    """

    def __init__(self, api_key: str, model: str = _GEMINI_EMBEDDING_MODEL):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        self._embedder = GoogleGenerativeAIEmbeddings(
            model=model,
            google_api_key=api_key,
            task_type="semantic_similarity",
            output_dimensionality=_OUTPUT_DIM,
        )

    async def embed_text(self, texts: list[str]) -> list[list[float]]:
        """Return one unit vector per input string (blocking call in thread pool)."""
        if not texts:
            return []

        def _call() -> list[list[float]]:
            return self._embedder.embed_documents(texts)

        return await asyncio.to_thread(_call)


@lru_cache(maxsize=1)
def get_gemini_text_embedder(api_key: str) -> GeminiTextEmbeddingAdapter:
    """Singleton — one adapter instance reused across all API requests."""
    return GeminiTextEmbeddingAdapter(api_key=api_key)
