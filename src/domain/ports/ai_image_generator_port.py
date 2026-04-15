"""Port for AI image generators (Pollinations, Imagen)."""
from __future__ import annotations

from typing import Protocol


class AIImageGeneratorPort(Protocol):
    name: str

    async def generate(self, prompt: str) -> bytes: ...
