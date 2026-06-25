"""Text embedding adapter backed by OpenAI embeddings."""

from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI


class OpenAITextEmbeddingAdapter:
    """Embed meal-cache text into provider-versioned OpenAI vectors."""

    def __init__(self, *, api_key: str, model: str, dimensions: int) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    async def embed_text(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dimensions,
            encoding_format="float",
        )
        return [item.embedding for item in response.data]


@lru_cache(maxsize=1)
def get_openai_text_embedder(
    api_key: str,
    model: str,
    dimensions: int,
) -> OpenAITextEmbeddingAdapter:
    return OpenAITextEmbeddingAdapter(
        api_key=api_key,
        model=model,
        dimensions=dimensions,
    )
