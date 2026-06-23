"""Unit tests — CloudflareWorkersAIProvider vision gateway header injection."""
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.infra.services.ai.providers.cloudflare_workers_ai_provider import CloudflareWorkersAIProvider


def _make_provider(gateway_id: str) -> CloudflareWorkersAIProvider:
    p = CloudflareWorkersAIProvider(
        account_id="acct",
        api_token="tok",
        text_model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        gateway_id=gateway_id,
        vision_enabled=True,
        vision_model="@cf/google/gemma-4-26b-a4b-it",
    )
    # Explicit guard from red-team Finding 1 — self._gateway_id must be stored
    assert p._gateway_id == gateway_id
    return p


def _make_httpx_mock(captured_headers: dict):
    """
    Build an AsyncClient context manager mock with AsyncMock for __aenter__/__aexit__.
    httpx.AsyncClient is used as `async with AsyncClient() as client:` — __aenter__
    must be a coroutine, otherwise `await` raises TypeError.
    """
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"result": {"response": '{"foods":[],"is_food":false}'}}

    async def fake_post(url, json, headers):
        captured_headers.update(headers)
        return mock_resp

    mock_inner = MagicMock()
    mock_inner.post = AsyncMock(side_effect=fake_post)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_inner)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_client_cls = MagicMock(return_value=mock_cm)
    return mock_client_cls


@pytest.mark.asyncio
async def test_gateway_headers_injected_when_gateway_id_set():
    provider = _make_provider("gw-123")
    captured_headers: dict = {}

    with patch(
        "src.infra.services.ai.providers.cloudflare_workers_ai_provider.httpx.AsyncClient",
        _make_httpx_mock(captured_headers),
    ):
        await provider._post_workers_ai("@cf/google/gemma-4-26b-a4b-it", {}, purpose="meal_scan")

    assert captured_headers["cf-aig-gateway-id"] == "gw-123"
    assert captured_headers["cf-aig-skip-cache"] == "true"
    assert captured_headers["cf-aig-collect-log-payload"] == "false"
    assert json.loads(captured_headers["cf-aig-metadata"]) == {"purpose": "meal_scan"}


@pytest.mark.asyncio
async def test_no_gateway_headers_when_gateway_id_empty():
    provider = _make_provider("")
    captured_headers: dict = {}

    with patch(
        "src.infra.services.ai.providers.cloudflare_workers_ai_provider.httpx.AsyncClient",
        _make_httpx_mock(captured_headers),
    ):
        await provider._post_workers_ai("@cf/google/gemma-4-26b-a4b-it", {}, purpose="meal_scan")

    assert "cf-aig-gateway-id" not in captured_headers
    assert "cf-aig-skip-cache" not in captured_headers
    assert "cf-aig-collect-log-payload" not in captured_headers


@pytest.mark.asyncio
async def test_no_metadata_header_when_purpose_empty():
    provider = _make_provider("gw-abc")
    captured_headers: dict = {}

    with patch(
        "src.infra.services.ai.providers.cloudflare_workers_ai_provider.httpx.AsyncClient",
        _make_httpx_mock(captured_headers),
    ):
        await provider._post_workers_ai("@cf/google/gemma-4-26b-a4b-it", {}, purpose="")

    assert "cf-aig-gateway-id" in captured_headers
    assert "cf-aig-metadata" not in captured_headers
