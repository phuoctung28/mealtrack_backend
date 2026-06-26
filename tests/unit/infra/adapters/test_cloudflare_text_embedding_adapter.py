from unittest.mock import AsyncMock

import pytest

from src.infra.adapters.cloudflare_text_embedding_adapter import (
    CloudflareTextEmbeddingAdapter,
)


class _Response:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_embed_text_posts_to_workers_ai_and_returns_vectors():
    client = AsyncMock()
    client.post = AsyncMock(
        return_value=_Response(
            {
                "result": {
                    "shape": [2, 3],
                    "data": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                }
            }
        )
    )
    adapter = CloudflareTextEmbeddingAdapter(
        account_id="acct",
        api_token="token",
        model="@cf/google/embeddinggemma-300m",
        dimensions=3,
        client=client,
    )

    result = await adapter.embed_text(["rice", "chicken"])

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    call_kwargs = client.post.await_args.kwargs
    assert client.post.await_args.args[0].endswith(
        "/accounts/acct/ai/run/@cf/google/embeddinggemma-300m"
    )
    assert call_kwargs["headers"] == {"Authorization": "Bearer token"}
    assert call_kwargs["json"] == {"text": ["rice", "chicken"]}


@pytest.mark.asyncio
async def test_embed_text_returns_empty_list_without_api_call():
    client = AsyncMock()
    adapter = CloudflareTextEmbeddingAdapter(
        account_id="acct",
        api_token="token",
        model="@cf/google/embeddinggemma-300m",
        dimensions=768,
        client=client,
    )

    assert await adapter.embed_text([]) == []
    client.post.assert_not_called()


@pytest.mark.asyncio
async def test_embed_text_rejects_dimension_mismatch():
    client = AsyncMock()
    client.post = AsyncMock(
        return_value=_Response({"result": {"data": [[0.1, 0.2]]}})
    )
    adapter = CloudflareTextEmbeddingAdapter(
        account_id="acct",
        api_token="token",
        model="@cf/google/embeddinggemma-300m",
        dimensions=768,
        client=client,
    )

    with pytest.raises(RuntimeError, match="dimension mismatch"):
        await adapter.embed_text(["rice"])
