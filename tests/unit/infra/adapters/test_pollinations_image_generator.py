import pytest
import httpx

from src.infra.adapters.pollinations_image_generator import PollinationsImageGenerator


@pytest.mark.asyncio
async def test_generate_returns_bytes():
    async def handler(request):
        assert "grilled%20salmon" in str(request.url).lower()
        return httpx.Response(
            200, content=b"\x89PNGfake", headers={"content-type": "image/png"}
        )

    gen = PollinationsImageGenerator(
        base_url="https://image.pollinations.ai/prompt",
        timeout=5,
        transport=httpx.MockTransport(handler),
    )
    out = await gen.generate("grilled salmon")
    assert out.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_generate_raises_on_non_200():
    async def handler(request):
        return httpx.Response(500, content=b"boom")

    gen = PollinationsImageGenerator(
        base_url="https://image.pollinations.ai/prompt",
        timeout=5,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(RuntimeError):
        await gen.generate("x")
