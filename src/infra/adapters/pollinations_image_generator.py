"""Pollinations.ai free image generator."""

from __future__ import annotations

import urllib.parse
from typing import Optional

import httpx


class PollinationsImageGenerator:
    name = "pollinations"

    def __init__(
        self,
        base_url: str,
        timeout: int,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    async def generate(self, prompt: str) -> bytes:
        encoded = urllib.parse.quote(prompt, safe="")
        url = f"{self._base_url}/{encoded}?nologo=true"
        async with httpx.AsyncClient(
            timeout=self._timeout, transport=self._transport
        ) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Pollinations returned {resp.status_code}: {resp.text[:200]}"
            )
        return resp.content
