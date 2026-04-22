"""
Deterministic fake: hash(text) seeds a random generator → unit-norm 512-d vector.
Used in tests so we don't need torch/CLIP.
"""

from __future__ import annotations

import hashlib
import math
import random


class FakeEmbeddingAdapter:
    def __init__(self, dim: int = 512):
        self._dim = dim

    async def embed_text(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    async def embed_image_bytes(self, data: bytes) -> list[float]:
        return self._vec(hashlib.sha256(data).hexdigest())

    def _vec(self, seed_source: str) -> list[float]:
        rng = random.Random(hashlib.sha256(seed_source.encode()).hexdigest())
        raw = [rng.gauss(0, 1) for _ in range(self._dim)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]
