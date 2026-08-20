"""Build a compact scene signature from meal photo bytes.

The signature is intentionally coarse so moderate camera-angle changes of the
same plated food on the same background still score highly, while clearly
different scenes do not.
"""

from __future__ import annotations

import math
from io import BytesIO

from PIL import Image

SCENE_GRID = 4
SCENE_DIM = SCENE_GRID * SCENE_GRID * 3  # 48 floats in 0..1


def build_scene_signature(image_bytes: bytes) -> list[float]:
    """Return a unit-ish 4x4 average-RGB grid signature."""
    with Image.open(BytesIO(image_bytes)) as img:
        rgb = img.convert("RGB")
        # Slight center bias: crop 10% borders so extreme wide-angle edges matter less
        w, h = rgb.size
        left = int(w * 0.08)
        top = int(h * 0.08)
        right = max(left + 1, int(w * 0.92))
        bottom = max(top + 1, int(h * 0.92))
        cropped = rgb.crop((left, top, right, bottom))
        small = cropped.resize((SCENE_GRID, SCENE_GRID), Image.Resampling.BOX)

    values: list[float] = []
    for y in range(SCENE_GRID):
        for x in range(SCENE_GRID):
            r, g, b = small.getpixel((x, y))
            values.extend((r / 255.0, g / 255.0, b / 255.0))
    return values


def scene_cosine_similarity(
    left: list[float] | tuple[float, ...], right: list[float] | tuple[float, ...]
) -> float:
    """Cosine similarity in [0, 1] for two scene signatures."""
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right, strict=True):
        dot += a * b
        left_norm += a * a
        right_norm += b * b
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (math.sqrt(left_norm) * math.sqrt(right_norm))))


def ingredient_jaccard(
    left: list[str] | tuple[str, ...],
    right: list[str] | tuple[str, ...],
) -> float:
    left_set = {item.strip().lower() for item in left if item and item.strip()}
    right_set = {item.strip().lower() for item in right if item and item.strip()}
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)
