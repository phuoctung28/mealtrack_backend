import pytest
import httpx

from src.infra.adapters.cloudflare_image_generator import CloudflareImageGenerator


def _gen(handler, account_id="acct123", api_token="tok123"):
    return CloudflareImageGenerator(
        account_id=account_id,
        api_token=api_token,
        timeout=5,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_generate_returns_bytes_on_success():
    async def handler(request):
        assert "/acct123/ai/run/@cf/black-forest-labs/flux-1-schnell" in str(request.url)
        assert request.headers["authorization"] == "Bearer tok123"
        return httpx.Response(
            200, content=b"\x89PNGfake", headers={"content-type": "image/png"}
        )

    out = await _gen(handler).generate("grilled salmon")
    assert out == b"\x89PNGfake"


@pytest.mark.asyncio
async def test_generate_raises_when_account_id_missing():
    async def handler(request):
        return httpx.Response(200, content=b"x", headers={"content-type": "image/png"})

    gen = CloudflareImageGenerator(
        account_id="", api_token="tok", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(RuntimeError, match="CF_ACCOUNT_ID"):
        await gen.generate("x")


@pytest.mark.asyncio
async def test_generate_raises_when_api_token_missing():
    async def handler(request):
        return httpx.Response(200, content=b"x", headers={"content-type": "image/png"})

    gen = CloudflareImageGenerator(
        account_id="acct", api_token="", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(RuntimeError, match="CF_API_TOKEN"):
        await gen.generate("x")


@pytest.mark.asyncio
async def test_generate_raises_on_401():
    async def handler(request):
        return httpx.Response(401, json={"errors": [{"message": "Unauthorized"}]})

    with pytest.raises(RuntimeError, match="401 Unauthorized"):
        await _gen(handler).generate("x")


@pytest.mark.asyncio
async def test_generate_raises_on_non_200():
    async def handler(request):
        return httpx.Response(500, content=b"internal error")

    with pytest.raises(RuntimeError, match="500"):
        await _gen(handler).generate("x")


@pytest.mark.asyncio
async def test_generate_raises_on_non_image_content_type():
    async def handler(request):
        return httpx.Response(
            200,
            content=b'{"result": "wrong"}',
            headers={"content-type": "application/json"},
        )

    with pytest.raises(RuntimeError, match="content-type"):
        await _gen(handler).generate("x")


@pytest.mark.asyncio
async def test_generate_raises_on_503():
    async def handler(request):
        return httpx.Response(503, content=b"model loading")

    with pytest.raises(RuntimeError, match="503"):
        await _gen(handler).generate("x")
