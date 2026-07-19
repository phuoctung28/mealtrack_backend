import json

import httpx
import pytest

from src.infra.adapters.cloudflare_workers_image_generator import (
    CloudflareWorkersImageGenerator,
)


@pytest.mark.asyncio
async def test_generate_url_posts_model_input_payload():
    async def handler(request):
        assert str(request.url).endswith("/accounts/account-1/ai/run")
        assert request.headers["Authorization"] == "Bearer token-1"
        payload = json.loads(request.content)
        assert payload["model"] == "openai/gpt-image-2"
        assert payload["input"]["prompt"] == "pho ga"
        assert payload["input"]["quality"] == "high"
        return httpx.Response(
            200,
            json={
                "result": {
                    "image": "https://pub-example.r2.dev/catalog/pho-ga.jpeg"
                },
                "state": "Completed",
            },
        )

    generator = CloudflareWorkersImageGenerator(
        account_id="account-1",
        api_token="token-1",
        transport=httpx.MockTransport(handler),
    )

    assert (
        await generator.generate_url("pho ga", quality="high")
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
