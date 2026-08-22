import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from src.infra.adapters.cloudflare_workers_image_generator import (
    CloudflareWorkersImageGenerator,
)


@pytest.mark.asyncio
async def test_generate_url_posts_model_input_payload():
    async def handler(request):
        assert str(request.url).endswith(
            "/accounts/account-1/ai/run/@cf/black-forest-labs/flux-2-klein-9b"
        )
        assert request.headers["Authorization"] == "Bearer token-1"
        assert "multipart/form-data" in request.headers["Content-Type"]
        body = request.content.decode("utf-8")
        assert 'name="prompt"' in body
        assert "pho ga" in body
        assert 'name="width"' in body
        assert "1024" in body
        return httpx.Response(
            200,
            json={
                "result": {"image": "iVBORw0KGgo="},
                "state": "Completed",
            },
        )

    image_store = SimpleNamespace(
        save_async=AsyncMock(
            return_value="https://res.cloudinary.com/test/image/upload/mealtrack/pho-ga.png"
        )
    )
    generator = CloudflareWorkersImageGenerator(
        account_id="account-1",
        api_token="token-1",
        transport=httpx.MockTransport(handler),
        image_store=image_store,
    )

    assert (
        await generator.generate_url("pho ga", quality="high")
        == "https://res.cloudinary.com/test/image/upload/mealtrack/pho-ga.png"
    )
    image_store.save_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_url_posts_json_for_legacy_url_model():
    async def handler(request):
        assert str(request.url).endswith("/accounts/account-1/ai/run")
        assert request.headers["Content-Type"] == "application/json"
        payload = json.loads(request.content)
        assert payload["model"] == "openai/gpt-image-2"
        assert payload["input"]["prompt"] == "pho ga"
        return httpx.Response(
            200,
            json={
                "result": {"image": "https://pub-example.r2.dev/catalog/pho-ga.jpeg"},
                "state": "Completed",
            },
        )

    generator = CloudflareWorkersImageGenerator(
        account_id="account-1",
        api_token="token-1",
        model="openai/gpt-image-2",
        transport=httpx.MockTransport(handler),
    )

    assert (
        await generator.generate_url("pho ga")
        == "https://pub-example.r2.dev/catalog/pho-ga.jpeg"
    )


@pytest.mark.asyncio
async def test_generate_url_raises_when_response_has_no_image_url():
    async def handler(request):
        return httpx.Response(200, json={"result": {}, "state": "Completed"})

    generator = CloudflareWorkersImageGenerator(
        account_id="account-1",
        api_token="token-1",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="missing result.image"):
        await generator.generate_url("pho ga")
