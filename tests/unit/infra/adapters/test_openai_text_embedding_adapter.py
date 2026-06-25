from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.infra.adapters.openai_text_embedding_adapter import OpenAITextEmbeddingAdapter


@pytest.mark.asyncio
async def test_embed_text_uses_dimensions_512():
    adapter = OpenAITextEmbeddingAdapter(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=512,
    )
    adapter._client.embeddings.create = AsyncMock(
        return_value=SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[0.1, 0.2]),
                SimpleNamespace(embedding=[0.3, 0.4]),
            ]
        )
    )

    result = await adapter.embed_text(["rice", "chicken"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    call_kwargs = adapter._client.embeddings.create.await_args.kwargs
    assert call_kwargs["model"] == "text-embedding-3-small"
    assert call_kwargs["dimensions"] == 512
    assert call_kwargs["input"] == ["rice", "chicken"]


@pytest.mark.asyncio
async def test_embed_text_returns_empty_list_without_api_call():
    adapter = OpenAITextEmbeddingAdapter(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=512,
    )
    adapter._client.embeddings.create = AsyncMock()

    assert await adapter.embed_text([]) == []
    adapter._client.embeddings.create.assert_not_called()
