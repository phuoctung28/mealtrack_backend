"""Text embedding adapter backed by Cloudflare Workers AI."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx


class CloudflareTextEmbeddingAdapter:
    """Embed meal-cache text into provider-versioned Workers AI vectors."""

    def __init__(
        self,
        *,
        account_id: str,
        api_token: str,
        model: str,
        dimensions: int,
        timeout_seconds: int = 30,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._account_id = account_id
        self._api_token = api_token
        self._model = model
        self._dimensions = dimensions
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def embed_text(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        data = await self._post_embeddings(texts)
        embeddings = data.get("result", {}).get("data")
        if not isinstance(embeddings, list):
            raise RuntimeError("Cloudflare embedding response missing result.data")
        if len(embeddings) != len(texts):
            raise RuntimeError(
                f"Cloudflare embedding count mismatch: got {len(embeddings)}, expected {len(texts)}"
            )

        vectors: list[list[float]] = []
        for embedding in embeddings:
            if not isinstance(embedding, list):
                raise RuntimeError("Cloudflare embedding response contains non-list vector")
            if len(embedding) != self._dimensions:
                raise RuntimeError(
                    f"Cloudflare embedding dimension mismatch: got {len(embedding)}, expected {self._dimensions}"
                )
            vectors.append([float(value) for value in embedding])
        return vectors

    async def _post_embeddings(self, texts: list[str]) -> dict[str, Any]:
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{self._account_id}"
            f"/ai/run/{self._model}"
        )
        headers = {"Authorization": f"Bearer {self._api_token}"}
        payload = {"text": texts}

        if self._client is not None:
            response = await self._client.post(url, headers=headers, json=payload)
        else:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)

        if response.status_code >= 400:
            raise RuntimeError(
                f"Cloudflare Workers AI embeddings returned {response.status_code}: {response.text[:300]}"
            )
        return response.json()


@lru_cache(maxsize=1)
def get_cloudflare_text_embedder(
    account_id: str,
    api_token: str,
    model: str,
    dimensions: int,
    timeout_seconds: int,
) -> CloudflareTextEmbeddingAdapter:
    return CloudflareTextEmbeddingAdapter(
        account_id=account_id,
        api_token=api_token,
        model=model,
        dimensions=dimensions,
        timeout_seconds=timeout_seconds,
    )
