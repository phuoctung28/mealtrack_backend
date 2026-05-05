import base64
import json

import pytest
import httpx

from src.infra.adapters.cloudflare_image_generator import CloudflareImageGenerator

# Minimal 1×1 white JPEG in base64 — matches what CF Workers AI actually returns
_FAKE_JPEG = b"\xff\xd8\xff\xe0fake"
_FAKE_B64 = base64.b64encode(_FAKE_JPEG).decode()


def _gen(handler, account_id="acct123", api_token="tok123"):
    return CloudflareImageGenerator(
        account_id=account_id,
        api_token=api_token,
        timeout=5,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_generate_returns_bytes_from_json_response():
    """Real CF Workers AI path: JSON envelope with base64-encoded image."""

    async def handler(request):
        assert "/acct123/ai/run/@cf/black-forest-labs/flux-1-schnell" in str(
            request.url
        )
        assert request.headers["authorization"] == "Bearer tok123"
        body = json.dumps({"result": {"image": _FAKE_B64}, "success": True})
        return httpx.Response(
            200, content=body.encode(), headers={"content-type": "application/json"}
        )

    out = await _gen(handler).generate("grilled salmon")
    assert out == _FAKE_JPEG


@pytest.mark.asyncio
async def test_generate_returns_bytes_from_raw_binary_response():
    """Fallback path: direct image/png bytes (some CF endpoints)."""

    async def handler(request):
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
async def test_generate_raises_on_malformed_json_missing_image_key():
    """JSON response but result.image is absent — extract fails cleanly."""

    async def handler(request):
        body = json.dumps({"result": {"something_else": "oops"}, "success": True})
        return httpx.Response(
            200, content=body.encode(), headers={"content-type": "application/json"}
        )

    with pytest.raises(RuntimeError, match="could not extract image"):
        await _gen(handler).generate("x")


@pytest.mark.asyncio
async def test_generate_raises_on_unknown_content_type():
    """Non-image, non-JSON content-type raises with content-type in message."""

    async def handler(request):
        return httpx.Response(
            200, content=b"unexpected", headers={"content-type": "text/plain"}
        )

    with pytest.raises(RuntimeError, match="content-type"):
        await _gen(handler).generate("x")


@pytest.mark.asyncio
async def test_generate_raises_on_503():
    async def handler(request):
        return httpx.Response(503, content=b"model loading")

    with pytest.raises(RuntimeError, match="503"):
        await _gen(handler).generate("x")
