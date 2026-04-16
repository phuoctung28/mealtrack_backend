"""HuggingFace Inference API image generator (free tier).

Uses FLUX.1-schnell by default — fast, high-quality food photos.
Free tier: ~1000 calls/day for public models with an HF token.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_HF_INFERENCE_BASE = "https://api-inference.huggingface.co/models"


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
        url = f"{_HF_INFERENCE_BASE}/{self._model}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {"inputs": prompt}

        async with httpx.AsyncClient(
            timeout=self._timeout, transport=self._transport
        ) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code == 503:
            # Model is loading — HF returns 503 with estimated wait time
            raise RuntimeError(
                f"HuggingFace model {self._model} is loading (503). "
                "Retry in a few seconds."
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"HuggingFace returned {resp.status_code}: {resp.text[:200]}"
            )

        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type:
            raise RuntimeError(
                f"HuggingFace returned unexpected content-type '{content_type}': "
                f"{resp.text[:200]}"
            )

        return resp.content
