"""HuggingFace Inference API image generator (free tier).

Uses FLUX.1-schnell by default — fast, high-quality food photos.
Free tier: available with a free HF token via the router endpoint.

HF migrated newer models (FLUX, etc.) from the legacy endpoint:
  api-inference.huggingface.co/models/{id}          ← returns 404 for FLUX
to the new router:
  router.huggingface.co/hf-inference/models/{id}    ← correct
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# New router endpoint — works for FLUX.1-schnell and other modern models.
# The legacy api-inference.huggingface.co URL returns 404 for these models.
_HF_INFERENCE_BASE = "https://router.huggingface.co/hf-inference/models"


class HuggingFaceImageGenerator:
    name = "huggingface"

    def __init__(
        self,
        api_key: str,
        model: str = "black-forest-labs/FLUX.1-schnell",
        timeout: int = 60,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._transport = transport

    async def generate(self, prompt: str) -> bytes:
        if not self._api_key:
            raise RuntimeError(
                "HUGGINGFACE_API_KEY is not set. "
                "Add it at huggingface.co/settings/tokens and set it as a GitHub secret."
            )

        url = f"{_HF_INFERENCE_BASE}/{self._model}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"inputs": prompt}

        logger.info("requesting HF image for prompt: %s", prompt[:80])

        async with httpx.AsyncClient(
            timeout=self._timeout, transport=self._transport
        ) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code == 401:
            raise RuntimeError(
                "HuggingFace returned 401 Unauthorized — check your HUGGINGFACE_API_KEY."
            )
        if resp.status_code == 503:
            raise RuntimeError(
                f"HuggingFace model {self._model} is loading (503). Retry shortly."
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"HuggingFace returned {resp.status_code}: {resp.text[:300]}"
            )

        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type:
            raise RuntimeError(
                f"HuggingFace returned unexpected content-type '{content_type}': "
                f"{resp.text[:200]}"
            )

        logger.info(
            "HF image generated: model=%s size=%d bytes", self._model, len(resp.content)
        )
        return resp.content
