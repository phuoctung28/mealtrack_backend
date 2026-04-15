"""Google Imagen 3 via AI Studio REST API. Fallback after Pollinations."""

from __future__ import annotations

import base64
from typing import Optional

import httpx


class ImagenImageGenerator:
    name = "imagen"

    def __init__(
        self,
        api_key: str,
        timeout: int,
        model: str = "imagen-3.0-generate-002",
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self._api_key = api_key
        self._timeout = timeout
        self._model = model
        self._transport = transport

    async def generate(self, prompt: str) -> bytes:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:predict?key={self._api_key}"
        )
        payload = {"instances": [{"prompt": prompt}], "parameters": {"sampleCount": 1}}
        async with httpx.AsyncClient(
            timeout=self._timeout, transport=self._transport
        ) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Imagen returned {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        preds = data.get("predictions") or []
        if not preds:
            raise RuntimeError(f"Imagen returned no predictions: {data}")
        b64 = preds[0].get("bytesBase64Encoded")
        if not b64:
            raise RuntimeError(f"Imagen response missing image bytes: {preds[0]}")
        return base64.b64decode(b64)
