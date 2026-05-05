import pytest

from src.infra.adapters.clip_embedding_adapter import ClipEmbeddingAdapter

DIM = 768


class _FakeProcessor:
    """Minimal processor stub — returns tensors the fake model can consume."""

    def __call__(self, **kwargs):
        torch = pytest.importorskip("torch")
        batch = 1
        if "text" in kwargs and kwargs["text"] is not None:
            batch = len(kwargs["text"])
        return {"input_ids": torch.zeros(batch, 64, dtype=torch.long)}


class _FakeModel:
    def eval(self):
        return self

    def get_text_features(self, **kwargs):
        torch = pytest.importorskip("torch")
        batch = kwargs["input_ids"].shape[0]
        return torch.randn(batch, DIM)

    def get_image_features(self, **kwargs):
        torch = pytest.importorskip("torch")
        return torch.randn(1, DIM)

    def __call__(self, **kwargs):
        torch = pytest.importorskip("torch")

        class _Out:
            logits_per_image = torch.tensor([[2.0]])  # sigmoid(2.0) ≈ 0.88

        return _Out()


@pytest.mark.asyncio
async def test_embed_text_returns_vector_per_input():
    pytest.importorskip("torch")
    adapter = ClipEmbeddingAdapter(
        processor=_FakeProcessor(), model=_FakeModel(), dim=DIM
    )
    out = await adapter.embed_text(["a", "b"])
    assert len(out) == 2
    assert len(out[0]) == DIM


@pytest.mark.asyncio
async def test_embed_image_bytes_returns_single_vector():
    pytest.importorskip("torch")
    adapter = ClipEmbeddingAdapter(
        processor=_FakeProcessor(), model=_FakeModel(), dim=DIM
    )
    one_px_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff"
        b"\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    out = await adapter.embed_image_bytes(one_px_png)
    assert len(out) == DIM


@pytest.mark.asyncio
async def test_score_image_text_returns_float_in_unit_interval():
    pytest.importorskip("torch")
    adapter = ClipEmbeddingAdapter(
        processor=_FakeProcessor(), model=_FakeModel(), dim=DIM
    )
    one_px_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff"
        b"\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    score = await adapter.score_image_text(one_px_png, "grilled salmon")
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
