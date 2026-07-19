"""Cloudflare Workers AI image generation adapter."""

from __future__ import annotations

import httpx


class CloudflareWorkersImageGenerator:
    """Generate image URLs through Cloudflare Workers AI."""

    name = "cloudflare-workers-ai"

    def __init__(
        self,
        *,
        account_id: str,
        api_token: str,
        model: str = "openai/gpt-image-2",
        timeout: int = 120,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._account_id = account_id.strip()
        self._api_token = api_token.strip()
        self._model = model.strip()
        self._timeout = timeout
        self._transport = transport
        if not self._account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID is required")
        if not self._api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN is required")
        if not self._model:
            raise ValueError("Cloudflare image model is required")

    async def generate_url(
        self,
        prompt: str,
        *,
        quality: str = "medium",
        size: str = "1024x1024",
        output_format: str = "jpeg",
    ) -> str:
        payload = {
            "model": self._model,
            "input": {
                "prompt": prompt,
                "quality": quality,
                "size": size,
                "output_format": output_format,
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self._account_id}/ai/run"
        )
        async with httpx.AsyncClient(
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(
                f"Cloudflare image generation returned {response.status_code}: "
                f"{response.text[:200]}"
            )
        return _extract_image_url(response.json())


def _extract_image_url(payload: dict) -> str:
    result = payload.get("result")
    if isinstance(result, dict):
        image = result.get("image")
        if isinstance(image, str) and image.startswith("https://"):
            return image
    errors = payload.get("errors")
    if errors:
        raise RuntimeError(f"Cloudflare image generation failed: {errors}")
    raise RuntimeError("Cloudflare image generation response missing result.image URL")
