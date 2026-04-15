import pytest

from src.infra.adapters.clip_embedding_adapter import ClipEmbeddingAdapter


class _FakeClipModel:
    def encode(self, inputs, convert_to_numpy=True, normalize_embeddings=True):
        import numpy as np
        return np.array([[float(i)] * 512 for i, _ in enumerate(inputs)])


@pytest.mark.asyncio
async def test_embed_text_returns_vector_per_input():
    adapter = ClipEmbeddingAdapter(model=_FakeClipModel(), dim=512)
    out = await adapter.embed_text(["a", "b"])
    assert len(out) == 2 and len(out[0]) == 512


@pytest.mark.asyncio
async def test_embed_image_bytes_returns_single_vector():
    adapter = ClipEmbeddingAdapter(model=_FakeClipModel(), dim=512)
    one_px_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff"
        b"\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    out = await adapter.embed_image_bytes(one_px_png)
    assert len(out) == 512
