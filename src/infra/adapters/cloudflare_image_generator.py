"""Cloudflare Workers AI image generator.

Uses @cf/black-forest-labs/flux-1-schnell on Cloudflare Workers AI.
Free tier: 10,000 neurons/day (~5-20 free images/day = ~150-600/month).
Paid tier: ~$0.001-0.002/image beyond free tier.

API endpoint:
  POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}
  Authorization: Bearer {api_token}
  Body: {"prompt": "..."}
  Response: application/json → {"result": {"image": "<base64-jpeg>"}, "success": true, ...}
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_CF_AI_BASE = "https://api.cloudflare.com/client/v4/accounts"
_CF_DEFAULT_MODEL = "@cf/black-forest-labs/flux-1-schnell"


class CloudflareImageGenerator:
    name = "cloudflare"

    def __init__(
        self,
        account_id: str,
        api_token: str,
        model: str = _CF_DEFAULT_MODEL,
        timeout: int = 60,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self._account_id = account_id
        self._api_token = api_token
        self._model = model
        self._timeout = timeout
        self._transport = transport

    async def generate(self, prompt: str) -> bytes:
        if not self._account_id:
            raise RuntimeError(
                "CF_ACCOUNT_ID is not set. "
                "Find it at dash.cloudflare.com → right sidebar → Account ID."
            )
        if not self._api_token:
            raise RuntimeError(
                "CF_API_TOKEN is not set. "
                "Create one at dash.cloudflare.com → My Profile → API Tokens "
                "with 'Workers AI' read permission."
            )

        url = f"{_CF_AI_BASE}/{self._account_id}/ai/run/{self._model}"
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

        logger.debug("requesting CF Workers AI image for prompt: %s", prompt[:80])

        async with httpx.AsyncClient(
            timeout=self._timeout, transport=self._transport
        ) as client:
            resp = await client.post(url, json={"prompt": prompt}, headers=headers)

        if resp.status_code == 401:
            raise RuntimeError(
                "Cloudflare returned 401 Unauthorized — check your CF_API_TOKEN."
            )
        if resp.status_code == 503:
            raise RuntimeError(
                f"Cloudflare Workers AI model {self._model} is unavailable (503). Retry shortly."
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Cloudflare Workers AI returned {resp.status_code}: {resp.text[:300]}"
            )

        content_type = resp.headers.get("content-type", "")

        if "image" in content_type:
            # Direct binary response (some CF endpoints / future models)
            image_bytes = resp.content
        elif "json" in content_type:
            # Standard CF Workers AI REST response:
            # {"result": {"image": "<base64-jpeg>"}, "success": true, ...}
            try:
                data = resp.json()
                b64 = data["result"]["image"]
                image_bytes = base64.b64decode(b64)
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"Cloudflare returned JSON but could not extract image: {resp.text[:300]}"
                ) from exc
        else:
            raise RuntimeError(
                f"Cloudflare returned unexpected content-type '{content_type}': "
                f"{resp.content[:200]!r}"
            )

        logger.debug(
            "CF image generated: model=%s size=%d bytes", self._model, len(image_bytes)
        )
        return image_bytes
